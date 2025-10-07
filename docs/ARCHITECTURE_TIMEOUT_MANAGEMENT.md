# Architecture: Système de Gestion des Timeouts & Rollback

**Date**: 7 octobre 2025
**Version**: 1.0
**Statut**: 📋 Planifié pour Phase 2

---

## 🎯 Vue d'Ensemble

Système robuste de gestion des timeouts avec:
1. **Rollback automatique** des données en cas de timeout/erreur
2. **Notifications utilisateur** temps réel avec diagnostic précis
3. **Recommandations intelligentes** (vérifier quotas, créditer compte)
4. **Retry automatique** après correction du problème
5. **Monitoring préventif** des quotas API

---

## 🏗️ Architecture Générale

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE CELERY                          │
│  process_tender_documents(tender_id)                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              TRANSACTION SERVICE                            │
│  - Crée savepoint à chaque étape                           │
│  - Tracks progression (STEP 1/6 → STEP 6/6)               │
│  - Rollback automatique si timeout                         │
└─────────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
┌────────────────────────┐  ┌──────────────────────┐
│   QUOTA MONITOR        │  │  TIMEOUT DETECTOR    │
│  - Track usage         │  │  - Wrap API calls    │
│  - Alertes 80%         │  │  - Detect timeouts   │
│  - Pre-check retry     │  │  - Classify errors   │
└────────────────────────┘  └──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            NOTIFICATION SERVICE                             │
│  - WebSocket temps réel                                     │
│  - Email avec diagnostic                                    │
│  - Recommandations actionnables                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              RETRY ENDPOINT                                 │
│  POST /tenders/{id}/retry                                   │
│  - Analyse cause échec                                      │
│  - Pré-vérification quotas                                  │
│  - Relance pipeline avec état restauré                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Composantes du Système

### 1. Exceptions Custom

**Fichier**: `backend/app/core/exceptions.py`

```python
"""
Custom exceptions for timeout and error handling.
"""
from typing import Dict, Any, Optional


class ScorpiusError(Exception):
    """Base exception for all ScorpiusAO errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        recommendations: Optional[list[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recommendations = recommendations or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception for API response."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.error_code,
            "details": self.details,
            "recommendations": self.recommendations
        }


# ============ TIMEOUT ERRORS ============

class TimeoutError(ScorpiusError):
    """Base class for all timeout errors."""
    pass


class OpenAITimeoutError(TimeoutError):
    """OpenAI API timeout (embeddings creation)."""

    def __init__(
        self,
        message: str = "OpenAI API request timed out",
        chunks_completed: int = 0,
        chunks_total: int = 0,
        elapsed_time: float = 0.0
    ):
        details = {
            "api": "OpenAI",
            "operation": "embeddings.create",
            "chunks_completed": chunks_completed,
            "chunks_total": chunks_total,
            "elapsed_time_seconds": elapsed_time,
            "progress_percent": (chunks_completed / chunks_total * 100) if chunks_total > 0 else 0
        }

        recommendations = [
            "🔍 Vérifier quota OpenAI: https://platform.openai.com/account/usage",
            "💳 Vérifier méthode de paiement OpenAI",
            "⏱️ Le timeout suggère une charge API élevée. Réessayer dans 5-10 minutes",
            "📊 Optimisation disponible: Activer batch processing (-95% temps)"
        ]

        super().__init__(
            message=message,
            error_code="OPENAI_TIMEOUT",
            details=details,
            recommendations=recommendations
        )


class ClaudeTimeoutError(TimeoutError):
    """Claude API timeout (analysis/criteria extraction)."""

    def __init__(
        self,
        message: str = "Claude API request timed out",
        operation: str = "analysis",
        prompt_length: int = 0,
        elapsed_time: float = 0.0
    ):
        details = {
            "api": "Claude (Anthropic)",
            "operation": operation,
            "prompt_length_chars": prompt_length,
            "elapsed_time_seconds": elapsed_time
        }

        recommendations = [
            "🔍 Vérifier quota Anthropic: https://console.anthropic.com/settings/usage",
            "💳 Vérifier crédits Anthropic",
            "📄 Le document peut être trop volumineux. Envisager réduire taille prompt",
            "⏱️ Réessayer dans quelques minutes"
        ]

        super().__init__(
            message=message,
            error_code="CLAUDE_TIMEOUT",
            details=details,
            recommendations=recommendations
        )


class CeleryTimeoutError(TimeoutError):
    """Celery task timeout (global pipeline)."""

    def __init__(
        self,
        message: str = "Celery task exceeded time limit",
        task_name: str = "",
        elapsed_time: float = 0.0,
        soft_limit: float = 0.0,
        hard_limit: float = 0.0
    ):
        details = {
            "task_name": task_name,
            "elapsed_time_seconds": elapsed_time,
            "soft_time_limit_seconds": soft_limit,
            "hard_time_limit_seconds": hard_limit
        }

        recommendations = [
            "🔄 Réessayer l'analyse (les données ont été rollback)",
            "⏱️ Si le problème persiste, vérifier les quotas API",
            "📊 Optimisation recommandée: Activer traitement parallèle des documents"
        ]

        super().__init__(
            message=message,
            error_code="CELERY_TIMEOUT",
            details=details,
            recommendations=recommendations
        )


# ============ QUOTA ERRORS ============

class QuotaError(ScorpiusError):
    """Base class for quota-related errors."""
    pass


class QuotaExceededError(QuotaError):
    """API quota exceeded."""

    def __init__(
        self,
        api_name: str,
        quota_type: str = "requests",
        current_usage: int = 0,
        quota_limit: int = 0,
        reset_time: Optional[str] = None
    ):
        details = {
            "api": api_name,
            "quota_type": quota_type,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "reset_time": reset_time
        }

        recommendations = [
            f"📊 Quota {api_name} dépassé ({current_usage}/{quota_limit})",
            "💳 Augmenter limite de quota dans le dashboard API",
            f"⏰ Quota se réinitialise à: {reset_time}" if reset_time else "⏰ Attendre réinitialisation quota",
            "🔄 Réessayer après augmentation quota"
        ]

        super().__init__(
            message=f"{api_name} quota exceeded ({current_usage}/{quota_limit})",
            error_code="QUOTA_EXCEEDED",
            details=details,
            recommendations=recommendations
        )


class InsufficientCreditsError(QuotaError):
    """Insufficient API credits."""

    def __init__(
        self,
        api_name: str,
        current_balance: float = 0.0,
        required_amount: float = 0.0,
        currency: str = "USD"
    ):
        details = {
            "api": api_name,
            "current_balance": current_balance,
            "required_amount": required_amount,
            "deficit": required_amount - current_balance,
            "currency": currency
        }

        recommendations = [
            f"💰 Crédits {api_name} insuffisants: {current_balance:.2f} {currency} (requis: {required_amount:.2f} {currency})",
            f"💳 Ajouter {(required_amount - current_balance):.2f} {currency} minimum",
            "🔗 Accéder au dashboard facturation",
            "🔄 Relancer l'analyse après rechargement crédits"
        ]

        super().__init__(
            message=f"Insufficient {api_name} credits: {current_balance:.2f}/{required_amount:.2f} {currency}",
            error_code="INSUFFICIENT_CREDITS",
            details=details,
            recommendations=recommendations
        )


# ============ DATABASE ERRORS ============

class DatabaseError(ScorpiusError):
    """Database operation errors."""
    pass


class RollbackError(DatabaseError):
    """Error during transaction rollback."""

    def __init__(
        self,
        message: str = "Failed to rollback transaction",
        savepoint_name: str = "",
        original_error: Optional[Exception] = None
    ):
        details = {
            "savepoint": savepoint_name,
            "original_error": str(original_error) if original_error else None
        }

        recommendations = [
            "⚠️ Erreur critique: Rollback impossible",
            "🔍 Vérifier intégrité base de données",
            "👨‍💻 Contacter administrateur système",
            "🗄️ Possible corruption de données - backup recommandé"
        ]

        super().__init__(
            message=message,
            error_code="ROLLBACK_FAILED",
            details=details,
            recommendations=recommendations
        )
```

---

### 2. Transaction Service (Savepoints & Rollback)

**Fichier**: `backend/app/services/transaction_service.py`

```python
"""
Transaction management service with savepoints and automatic rollback.
"""
import logging
from typing import Optional, Callable, Any
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import RollbackError

logger = logging.getLogger(__name__)


class TransactionService:
    """
    Manage database transactions with savepoints for safe rollback.

    Usage:
        with transaction_service.savepoint(db, "step_2_embeddings"):
            # Create embeddings...
            # If error occurs, auto-rollback to this savepoint
    """

    def __init__(self):
        self.savepoint_stack: list[str] = []

    @contextmanager
    def savepoint(
        self,
        db: Session,
        name: str,
        description: str = "",
        log_success: bool = True
    ):
        """
        Create a named savepoint for rollback.

        Args:
            db: SQLAlchemy session
            name: Savepoint identifier (e.g., "step_2_embeddings")
            description: Human-readable description for logs
            log_success: Whether to log successful completion

        Yields:
            None

        Raises:
            RollbackError: If rollback fails (critical error)
        """
        savepoint_id = f"sp_{name}_{int(datetime.utcnow().timestamp())}"
        self.savepoint_stack.append(savepoint_id)

        logger.info(f"📍 Creating savepoint: {name} ({description})")

        try:
            # Create nested savepoint
            nested = db.begin_nested()

            yield

            # Commit savepoint on success
            nested.commit()

            if log_success:
                logger.info(f"✅ Savepoint committed: {name}")

        except Exception as e:
            logger.error(f"❌ Error in {name}: {e}")
            logger.info(f"🔄 Rolling back to savepoint: {name}")

            try:
                # Rollback to this savepoint
                nested.rollback()
                logger.info(f"✅ Rollback successful: {name}")

            except SQLAlchemyError as rollback_error:
                logger.critical(f"💥 ROLLBACK FAILED for {name}: {rollback_error}")
                raise RollbackError(
                    message=f"Failed to rollback savepoint '{name}'",
                    savepoint_name=name,
                    original_error=rollback_error
                )

            # Re-raise original exception after successful rollback
            raise

        finally:
            if savepoint_id in self.savepoint_stack:
                self.savepoint_stack.remove(savepoint_id)

    def track_progress(
        self,
        db: Session,
        tender_id: str,
        current_step: int,
        total_steps: int,
        step_name: str,
        status: str = "in_progress"
    ):
        """
        Track pipeline progress for observability.

        Args:
            db: SQLAlchemy session
            tender_id: Tender UUID
            current_step: Current step number (1-6)
            total_steps: Total steps in pipeline (typically 6)
            step_name: Human-readable step name
            status: Step status (in_progress, completed, failed)
        """
        from app.models.tender_analysis import TenderAnalysis
        from sqlalchemy import select

        stmt = select(TenderAnalysis).where(TenderAnalysis.tender_id == tender_id)
        analysis = db.execute(stmt).scalar_one_or_none()

        if analysis:
            # Store progress in structured_data
            progress = analysis.structured_data or {}
            progress["pipeline_progress"] = {
                "current_step": current_step,
                "total_steps": total_steps,
                "step_name": step_name,
                "status": status,
                "progress_percent": int((current_step / total_steps) * 100),
                "last_updated": datetime.utcnow().isoformat()
            }

            analysis.structured_data = progress
            db.commit()

            logger.info(f"📊 Progress: [{current_step}/{total_steps}] {step_name} - {status}")

    def clear_partial_data(
        self,
        db: Session,
        tender_id: str,
        step_name: str
    ):
        """
        Clear partial data after timeout/error.

        Args:
            db: SQLAlchemy session
            tender_id: Tender UUID
            step_name: Step that failed (e.g., "step_2_embeddings")
        """
        from app.models.document import DocumentEmbedding
        from app.models.tender_analysis import TenderAnalysis
        from sqlalchemy import delete, select

        logger.info(f"🧹 Clearing partial data for tender {tender_id}, step: {step_name}")

        if step_name == "step_2_embeddings":
            # Delete partial embeddings for this tender
            from app.models.tender_document import TenderDocument

            # Get document IDs for this tender
            stmt = select(TenderDocument.id).where(TenderDocument.tender_id == tender_id)
            doc_ids = db.execute(stmt).scalars().all()

            if doc_ids:
                # Delete embeddings
                stmt = delete(DocumentEmbedding).where(DocumentEmbedding.document_id.in_(doc_ids))
                result = db.execute(stmt)
                logger.info(f"   Deleted {result.rowcount} partial embeddings")

        elif step_name == "step_3_analysis":
            # Clear analysis data
            stmt = select(TenderAnalysis).where(TenderAnalysis.tender_id == tender_id)
            analysis = db.execute(stmt).scalar_one_or_none()

            if analysis:
                analysis.summary = None
                analysis.key_requirements = []
                analysis.analysis_status = "failed"
                logger.info(f"   Cleared analysis data")

        db.commit()


# Global instance
transaction_service = TransactionService()
```

---

### 3. Notification Service

**Fichier**: `backend/app/services/notification_service.py`

```python
"""
User notification service (WebSocket + Email).
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Send notifications to users via WebSocket and Email.
    """

    def __init__(self):
        self.websocket_connections: Dict[str, Any] = {}  # user_id → connection

    async def notify_timeout(
        self,
        user_id: str,
        tender_id: str,
        tender_title: str,
        error: Any,  # ScorpiusError instance
        send_email: bool = True
    ):
        """
        Notify user of timeout error with diagnostic and recommendations.

        Args:
            user_id: User UUID
            tender_id: Tender UUID
            tender_title: Tender title for context
            error: ScorpiusError exception instance
            send_email: Whether to send email notification
        """
        error_dict = error.to_dict() if hasattr(error, 'to_dict') else {
            "error": str(type(error).__name__),
            "message": str(error)
        }

        # WebSocket notification (real-time)
        await self._send_websocket(
            user_id=user_id,
            event_type="pipeline_timeout",
            data={
                "tender_id": tender_id,
                "tender_title": tender_title,
                "timestamp": datetime.utcnow().isoformat(),
                "error": error_dict,
                "actions": [
                    {
                        "label": "Vérifier quotas API",
                        "action": "open_quota_dashboard"
                    },
                    {
                        "label": "Relancer l'analyse",
                        "action": "retry_analysis",
                        "endpoint": f"/api/v1/tenders/{tender_id}/retry"
                    }
                ]
            }
        )

        # Email notification
        if send_email:
            await self._send_email(
                user_id=user_id,
                subject=f"❌ Échec analyse: {tender_title}",
                template="timeout_error",
                context={
                    "tender_title": tender_title,
                    "error": error_dict,
                    "retry_url": f"https://scorpiusao.com/tenders/{tender_id}/retry"
                }
            )

        logger.info(f"📧 Notification sent to user {user_id} for tender {tender_id}")

    async def notify_quota_warning(
        self,
        user_id: str,
        api_name: str,
        current_usage: int,
        quota_limit: int,
        usage_percent: float
    ):
        """
        Send preventive warning when quota reaches 80%.

        Args:
            user_id: User UUID
            api_name: API name (OpenAI, Claude)
            current_usage: Current usage count
            quota_limit: Total quota limit
            usage_percent: Usage percentage (e.g., 82.5)
        """
        await self._send_websocket(
            user_id=user_id,
            event_type="quota_warning",
            data={
                "api": api_name,
                "current_usage": current_usage,
                "quota_limit": quota_limit,
                "usage_percent": round(usage_percent, 1),
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"⚠️ Quota {api_name} à {usage_percent:.0f}% ({current_usage}/{quota_limit})",
                "recommendations": [
                    f"Augmenter quota {api_name} avant dépassement",
                    "Vérifier crédits restants",
                    "Planifier rechargement si nécessaire"
                ]
            }
        )

        logger.warning(f"⚠️ Quota warning: {api_name} at {usage_percent:.1f}% for user {user_id}")

    async def notify_retry_success(
        self,
        user_id: str,
        tender_id: str,
        tender_title: str,
        processing_time: int
    ):
        """
        Notify user of successful retry.

        Args:
            user_id: User UUID
            tender_id: Tender UUID
            tender_title: Tender title
            processing_time: Processing time in seconds
        """
        await self._send_websocket(
            user_id=user_id,
            event_type="pipeline_success",
            data={
                "tender_id": tender_id,
                "tender_title": tender_title,
                "processing_time_seconds": processing_time,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"✅ Analyse complétée: {tender_title} ({processing_time}s)",
                "action": {
                    "label": "Voir l'analyse",
                    "url": f"/tenders/{tender_id}/analysis"
                }
            }
        )

        logger.info(f"✅ Success notification sent for tender {tender_id}")

    async def _send_websocket(
        self,
        user_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Send WebSocket notification (to be implemented)."""
        # TODO: Implement WebSocket broadcast
        logger.info(f"📡 WebSocket: {event_type} → user {user_id}")
        logger.debug(f"   Data: {json.dumps(data, indent=2)}")

    async def _send_email(
        self,
        user_id: str,
        subject: str,
        template: str,
        context: Dict[str, Any]
    ):
        """Send email notification (to be implemented)."""
        # TODO: Implement email service (SendGrid, AWS SES, etc.)
        logger.info(f"📧 Email: '{subject}' → user {user_id}")
        logger.debug(f"   Template: {template}")
        logger.debug(f"   Context: {json.dumps(context, indent=2)}")


# Global instance
notification_service = NotificationService()
```

---

### 4. Quota Monitor

**Fichier**: `backend/app/services/quota_monitor.py`

```python
"""
API quota monitoring service.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import QuotaExceededError, InsufficientCreditsError

logger = logging.getLogger(__name__)


class QuotaMonitor:
    """
    Monitor API quotas and send alerts.
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.warning_threshold = 0.8  # 80%

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self.redis is None:
            self.redis = await redis.from_url(settings.redis_url)
        return self.redis

    async def track_api_call(
        self,
        api_name: str,
        operation: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ):
        """
        Track API usage.

        Args:
            api_name: API name (openai, anthropic)
            operation: Operation type (embeddings, chat)
            tokens_used: Number of tokens consumed
            cost_usd: Cost in USD
        """
        redis_client = await self._get_redis()
        now = datetime.utcnow()
        date_key = now.strftime("%Y-%m-%d")

        # Keys for tracking
        calls_key = f"quota:{api_name}:calls:{date_key}"
        tokens_key = f"quota:{api_name}:tokens:{date_key}"
        cost_key = f"quota:{api_name}:cost:{date_key}"

        # Increment counters
        await redis_client.incr(calls_key)
        await redis_client.incrby(tokens_key, tokens_used)
        await redis_client.incrbyfloat(cost_key, cost_usd)

        # Set expiration (7 days)
        await redis_client.expire(calls_key, 7 * 24 * 3600)
        await redis_client.expire(tokens_key, 7 * 24 * 3600)
        await redis_client.expire(cost_key, 7 * 24 * 3600)

        logger.debug(f"📊 Tracked: {api_name}.{operation} - {tokens_used} tokens, ${cost_usd:.4f}")

    async def check_quota(
        self,
        api_name: str,
        required_tokens: int = 0,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if API quota allows operation.

        Args:
            api_name: API name (openai, anthropic)
            required_tokens: Tokens required for operation
            user_id: User ID for notification

        Returns:
            Dict with quota status and recommendations

        Raises:
            QuotaExceededError: If quota exceeded
            InsufficientCreditsError: If insufficient credits
        """
        redis_client = await self._get_redis()
        now = datetime.utcnow()
        date_key = now.strftime("%Y-%m-%d")

        # Get current usage
        tokens_key = f"quota:{api_name}:tokens:{date_key}"
        current_usage = int(await redis_client.get(tokens_key) or 0)

        # Get quota limits (stored in Redis or config)
        quota_limit = await self._get_quota_limit(api_name)

        # Calculate usage
        usage_percent = (current_usage / quota_limit * 100) if quota_limit > 0 else 0
        remaining = quota_limit - current_usage

        # Check if operation possible
        if current_usage + required_tokens > quota_limit:
            raise QuotaExceededError(
                api_name=api_name,
                quota_type="tokens",
                current_usage=current_usage,
                quota_limit=quota_limit,
                reset_time=self._get_next_reset_time()
            )

        # Warning if approaching limit
        if usage_percent >= self.warning_threshold * 100 and user_id:
            from app.services.notification_service import notification_service
            await notification_service.notify_quota_warning(
                user_id=user_id,
                api_name=api_name,
                current_usage=current_usage,
                quota_limit=quota_limit,
                usage_percent=usage_percent
            )

        return {
            "api": api_name,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "remaining": remaining,
            "usage_percent": round(usage_percent, 1),
            "can_proceed": remaining >= required_tokens,
            "warning": usage_percent >= self.warning_threshold * 100
        }

    async def _get_quota_limit(self, api_name: str) -> int:
        """Get quota limit for API (from config or database)."""
        # TODO: Fetch from database or external API
        defaults = {
            "openai": 1_000_000,  # 1M tokens/day
            "anthropic": 500_000   # 500k tokens/day
        }
        return defaults.get(api_name, 100_000)

    def _get_next_reset_time(self) -> str:
        """Get next quota reset time (midnight UTC)."""
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
        return midnight.isoformat() + "Z"

    async def get_usage_report(
        self,
        api_name: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get usage report for last N days.

        Args:
            api_name: Specific API or None for all
            days: Number of days to include

        Returns:
            Usage statistics
        """
        redis_client = await self._get_redis()
        now = datetime.utcnow()

        apis = [api_name] if api_name else ["openai", "anthropic"]
        report = {}

        for api in apis:
            daily_usage = []

            for i in range(days):
                date = now - timedelta(days=i)
                date_key = date.strftime("%Y-%m-%d")

                calls = int(await redis_client.get(f"quota:{api}:calls:{date_key}") or 0)
                tokens = int(await redis_client.get(f"quota:{api}:tokens:{date_key}") or 0)
                cost = float(await redis_client.get(f"quota:{api}:cost:{date_key}") or 0.0)

                daily_usage.append({
                    "date": date_key,
                    "calls": calls,
                    "tokens": tokens,
                    "cost_usd": round(cost, 2)
                })

            # Calculate totals
            total_calls = sum(d["calls"] for d in daily_usage)
            total_tokens = sum(d["tokens"] for d in daily_usage)
            total_cost = sum(d["cost_usd"] for d in daily_usage)

            report[api] = {
                "daily_usage": daily_usage,
                "totals": {
                    "calls": total_calls,
                    "tokens": total_tokens,
                    "cost_usd": round(total_cost, 2)
                },
                "averages": {
                    "calls_per_day": round(total_calls / days, 1),
                    "tokens_per_day": round(total_tokens / days, 1),
                    "cost_per_day_usd": round(total_cost / days, 2)
                }
            }

        return report


# Global instance
quota_monitor = QuotaMonitor()
```

---

### 5. Retry Endpoint

**Fichier**: `backend/app/api/v1/endpoints/retry.py`

```python
"""
Retry endpoint for failed tender analyses.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.models.tender_analysis import TenderAnalysis
from app.services.quota_monitor import quota_monitor
from app.tasks.tender_tasks import process_tender_documents

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tenders/{tender_id}/retry", response_model=Dict[str, Any])
async def retry_tender_analysis(
    tender_id: str,
    force: bool = False,  # Skip quota checks if true
    db: Session = Depends(get_db)
):
    """
    Retry failed tender analysis with pre-checks and recommendations.

    Args:
        tender_id: Tender UUID
        force: Skip quota pre-checks (use with caution)
        db: Database session

    Returns:
        Retry status and recommendations

    Raises:
        HTTPException: If pre-checks fail or tender not found
    """
    # 1. Get tender analysis
    analysis = db.query(TenderAnalysis).filter_by(tender_id=tender_id).first()

    if not analysis:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    if analysis.analysis_status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Tender analysis already completed. Use force=true to re-analyze."
        )

    # 2. Analyze previous error
    error_analysis = _analyze_previous_error(analysis)

    # 3. Pre-check quotas (unless forced)
    quota_checks = {}
    if not force:
        try:
            # Check OpenAI quota (embeddings)
            openai_status = await quota_monitor.check_quota(
                api_name="openai",
                required_tokens=10_000,  # Estimate for typical tender
                user_id=str(analysis.tender.user_id) if hasattr(analysis.tender, 'user_id') else None
            )
            quota_checks["openai"] = openai_status

            # Check Claude quota (analysis)
            claude_status = await quota_monitor.check_quota(
                api_name="anthropic",
                required_tokens=50_000,  # Estimate for analysis
                user_id=str(analysis.tender.user_id) if hasattr(analysis.tender, 'user_id') else None
            )
            quota_checks["anthropic"] = claude_status

            # Block retry if quotas insufficient
            if not openai_status["can_proceed"]:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Insufficient OpenAI quota",
                        "quota_status": openai_status,
                        "recommendations": [
                            "Augmenter quota OpenAI",
                            "Attendre réinitialisation quota",
                            "Vérifier crédits disponibles"
                        ]
                    }
                )

            if not claude_status["can_proceed"]:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Insufficient Claude quota",
                        "quota_status": claude_status,
                        "recommendations": [
                            "Augmenter quota Anthropic",
                            "Attendre réinitialisation quota",
                            "Vérifier crédits disponibles"
                        ]
                    }
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Quota pre-check failed: {e}. Proceeding anyway.")

    # 4. Reset analysis status
    analysis.analysis_status = "pending"
    analysis.error_message = None
    db.commit()

    # 5. Trigger retry (Celery task)
    task = process_tender_documents.delay(str(tender_id))

    logger.info(f"🔄 Retry triggered for tender {tender_id}, task: {task.id}")

    return {
        "status": "retry_started",
        "tender_id": tender_id,
        "task_id": task.id,
        "previous_error": error_analysis,
        "quota_checks": quota_checks if not force else {"skipped": True},
        "message": "L'analyse a été relancée. Vous serez notifié une fois terminée.",
        "recommendations": error_analysis.get("recommendations", [])
    }


def _analyze_previous_error(analysis: TenderAnalysis) -> Dict[str, Any]:
    """
    Analyze previous error to provide recommendations.

    Args:
        analysis: TenderAnalysis instance

    Returns:
        Error analysis with recommendations
    """
    error_message = analysis.error_message or ""

    # Classify error type
    if "OpenAI" in error_message or "openai" in error_message.lower():
        error_type = "openai_timeout"
        recommendations = [
            "✅ Pré-vérification: Quota OpenAI disponible",
            "⏱️ Temps d'ingestion optimisé avec batch processing",
            "🔄 Retry devrait réussir"
        ]
    elif "Claude" in error_message or "anthropic" in error_message.lower():
        error_type = "claude_timeout"
        recommendations = [
            "✅ Pré-vérification: Quota Claude disponible",
            "📄 Document sera traité par morceaux si trop volumineux",
            "🔄 Retry devrait réussir"
        ]
    elif "Celery" in error_message or "timeout" in error_message.lower():
        error_type = "celery_timeout"
        recommendations = [
            "✅ Timeout Celery augmenté",
            "⚡ Traitement parallèle activé",
            "🔄 Retry devrait réussir"
        ]
    elif "quota" in error_message.lower() or "limit" in error_message.lower():
        error_type = "quota_exceeded"
        recommendations = [
            "📊 Vérifier quotas API avant retry",
            "💳 Recharger crédits si nécessaire",
            "⏰ Attendre réinitialisation quota"
        ]
    else:
        error_type = "unknown"
        recommendations = [
            "🔍 Erreur non reconnue",
            "👨‍💻 Contacter support si le problème persiste"
        ]

    return {
        "error_type": error_type,
        "error_message": error_message,
        "analysis_status": analysis.analysis_status,
        "last_attempt": analysis.updated_at.isoformat() if analysis.updated_at else None,
        "recommendations": recommendations
    }
```

---

## 🔄 Flux de Gestion des Timeouts

### Scénario 1: Timeout OpenAI (Embeddings)

```
1. User triggers analysis → POST /tenders/{id}/analyze
2. Celery task starts → process_tender_documents()
3. STEP 2: Create embeddings
   │
   ├─ Transaction Service creates savepoint "step_2_embeddings"
   ├─ Quota Monitor checks OpenAI quota ✅
   ├─ Loop through documents:
   │  └─ ingest_document_sync() with batch processing
   │     │
   │     ├─ OpenAI API call times out after 30s ❌
   │     │
   │     └─ TIMEOUT DETECTED
   │        │
   │        ├─ Transaction Service rollbacks to savepoint
   │        ├─ Clear partial embeddings from database
   │        ├─ Update analysis status → "failed"
   │        ├─ Log detailed error + progress info
   │        │
   │        └─ Notification Service sends:
   │           ├─ WebSocket notification (real-time)
   │           │  └─ "❌ Timeout lors de la création des embeddings"
   │           │  └─ Progress: 47/92 chunks complétés
   │           │  └─ Actions: [Vérifier quota, Relancer]
   │           │
   │           └─ Email notification
   │              └─ Subject: "Échec analyse: VSGP-AO"
   │              └─ Body: Diagnostic + Recommandations
   │              └─ CTA: "Relancer l'analyse"
4. User checks quota OpenAI dashboard
5. User clicks "Relancer" → POST /tenders/{id}/retry
6. Retry endpoint:
   ├─ Analyzes previous error → OpenAI timeout
   ├─ Pre-checks OpenAI quota ✅ (sufficient)
   ├─ Pre-checks Claude quota ✅ (sufficient)
   └─ Triggers new Celery task
7. Pipeline executes successfully ✅
8. Notification Service sends success notification
```

---

### Scénario 2: Quota OpenAI Dépassé

```
1. User triggers analysis
2. Celery task starts
3. Quota Monitor checks OpenAI quota
   │
   └─ Current usage: 950,000 tokens
   └─ Quota limit: 1,000,000 tokens
   └─ Required: 100,000 tokens
   └─ QUOTA INSUFFICIENT ❌
4. QuotaExceededError raised
   │
   ├─ Transaction Service rollbacks
   ├─ Analysis status → "failed"
   │
   └─ Notification Service sends:
      ├─ WebSocket: "❌ Quota OpenAI dépassé (950k/1M)"
      │  └─ Recommendations:
      │     - "Augmenter quota OpenAI"
      │     - "Quota se réinitialise demain à 00:00 UTC"
      │     - "Relancer après augmentation quota"
      │
      └─ Email with links:
         - OpenAI usage dashboard
         - Retry endpoint
5. User increases OpenAI quota
6. User retries analysis → Success ✅
```

---

### Scénario 3: Warning Préventif (80% Quota)

```
1. Quota Monitor tracks API usage
2. OpenAI usage reaches 800,000 / 1,000,000 (80%)
3. Notification Service sends warning:
   │
   ├─ WebSocket notification (non-blocking)
   │  └─ "⚠️ Quota OpenAI à 80%"
   │  └─ "Restant: 200,000 tokens (~2 tenders)"
   │  └─ Recommendations:
   │     - "Augmenter quota avant dépassement"
   │     - "Planifier rechargement crédits"
   │
   └─ No email (non-urgent warning)
4. User has time to act before hitting limit
```

---

## 📊 Métriques de Suivi

### Endpoint GET /api/v1/quotas/status

```json
{
  "openai": {
    "current_usage": 425000,
    "quota_limit": 1000000,
    "remaining": 575000,
    "usage_percent": 42.5,
    "warning": false,
    "reset_time": "2025-10-08T00:00:00Z"
  },
  "anthropic": {
    "current_usage": 198000,
    "quota_limit": 500000,
    "remaining": 302000,
    "usage_percent": 39.6,
    "warning": false,
    "reset_time": "2025-10-08T00:00:00Z"
  },
  "last_7_days": {
    "openai": {
      "total_calls": 152,
      "total_tokens": 2975000,
      "total_cost_usd": 4.21,
      "avg_cost_per_day_usd": 0.60
    },
    "anthropic": {
      "total_calls": 48,
      "total_tokens": 1385000,
      "total_cost_usd": 16.62,
      "avg_cost_per_day_usd": 2.37
    }
  }
}
```

---

## 🧪 Tests à Implémenter

### Test 1: Rollback sur Timeout

```python
# tests/services/test_transaction_service.py

async def test_rollback_on_timeout(db_session):
    """Vérifier que les données sont rollback sur timeout."""

    # 1. Create initial data
    tender = Tender(title="Test Tender")
    db_session.add(tender)
    db_session.commit()

    # 2. Simulate timeout in savepoint
    try:
        with transaction_service.savepoint(db_session, "step_test", "Test timeout"):
            # Add embedding
            embedding = DocumentEmbedding(...)
            db_session.add(embedding)

            # Simulate timeout
            raise OpenAITimeoutError(chunks_completed=10, chunks_total=100)

    except OpenAITimeoutError:
        pass  # Expected

    # 3. Verify rollback
    embeddings = db_session.query(DocumentEmbedding).all()
    assert len(embeddings) == 0, "Embeddings should be rolled back"

    # Tender should still exist (not in savepoint)
    tenders = db_session.query(Tender).all()
    assert len(tenders) == 1
```

### Test 2: Notification sur Timeout

```python
# tests/services/test_notification_service.py

async def test_notification_sent_on_timeout(mock_websocket, mock_email):
    """Vérifier envoi notifications sur timeout."""

    error = OpenAITimeoutError(
        chunks_completed=47,
        chunks_total=92,
        elapsed_time=180.5
    )

    await notification_service.notify_timeout(
        user_id="user-123",
        tender_id="tender-456",
        tender_title="VSGP-AO",
        error=error
    )

    # Verify WebSocket called
    assert mock_websocket.called
    ws_data = mock_websocket.call_args[1]["data"]
    assert ws_data["error"]["code"] == "OPENAI_TIMEOUT"
    assert len(ws_data["error"]["recommendations"]) > 0

    # Verify email called
    assert mock_email.called
    email_context = mock_email.call_args[1]["context"]
    assert email_context["tender_title"] == "VSGP-AO"
```

### Test 3: Pre-check Quotas Avant Retry

```python
# tests/api/test_retry.py

async def test_retry_blocked_if_quota_exceeded(client, db_session):
    """Vérifier que retry est bloqué si quota insuffisant."""

    # Mock quota check to return insufficient
    with patch('app.services.quota_monitor.check_quota') as mock_check:
        mock_check.return_value = {
            "can_proceed": False,
            "current_usage": 980000,
            "quota_limit": 1000000,
            "remaining": 20000
        }

        response = client.post(f"/api/v1/tenders/{tender_id}/retry")

        assert response.status_code == 429
        data = response.json()
        assert "Insufficient OpenAI quota" in data["detail"]["error"]
        assert len(data["detail"]["recommendations"]) > 0
```

---

## 📝 Checklist Implémentation

### Sprint 1 - Semaine 1

- [ ] **Exceptions Custom** (`app/core/exceptions.py`)
  - [ ] `TimeoutError` base class
  - [ ] `OpenAITimeoutError`
  - [ ] `ClaudeTimeoutError`
  - [ ] `CeleryTimeoutError`
  - [ ] `QuotaExceededError`
  - [ ] `InsufficientCreditsError`
  - [ ] Tests unitaires exceptions

- [ ] **Transaction Service** (`app/services/transaction_service.py`)
  - [ ] Méthode `savepoint()` context manager
  - [ ] Méthode `track_progress()`
  - [ ] Méthode `clear_partial_data()`
  - [ ] Tests rollback sur timeout
  - [ ] Tests savepoint stack

### Sprint 1 - Semaine 2

- [ ] **Notification Service** (`app/services/notification_service.py`)
  - [ ] Méthode `notify_timeout()`
  - [ ] Méthode `notify_quota_warning()`
  - [ ] Méthode `notify_retry_success()`
  - [ ] WebSocket integration (stub)
  - [ ] Email integration (stub)
  - [ ] Tests notifications

- [ ] **Quota Monitor** (`app/services/quota_monitor.py`)
  - [ ] Méthode `track_api_call()`
  - [ ] Méthode `check_quota()`
  - [ ] Méthode `get_usage_report()`
  - [ ] Redis integration
  - [ ] Tests monitoring

### Sprint 1 - Semaine 3

- [ ] **Retry Endpoint** (`app/api/v1/endpoints/retry.py`)
  - [ ] POST `/tenders/{id}/retry`
  - [ ] Pre-check quotas
  - [ ] Error analysis
  - [ ] Tests API retry

- [ ] **Integration Pipeline**
  - [ ] Modifier `process_tender_documents()` avec savepoints
  - [ ] Wrapper API calls avec timeout detection
  - [ ] Tests E2E timeout → rollback → notification → retry

---

## 💰 Estimation Coûts

### Développement

| Tâche | Effort | Coût |
|-------|--------|------|
| Exceptions custom | 0.5 jour | $400 |
| Transaction service | 1.5 jours | $1,200 |
| Notification service | 1 jour | $800 |
| Quota monitor | 1.5 jours | $1,200 |
| Retry endpoint | 0.5 jour | $400 |
| Integration pipeline | 1 jour | $800 |
| Tests | 1 jour | $800 |
| **Total** | **7 jours** | **$5,600** |

### Opérations (Mois)

| Service | Coût/Mois |
|---------|-----------|
| Redis (quota tracking) | $10 |
| Email (SendGrid/SES) | $15 |
| WebSocket (Socket.io/Pusher) | $25 |
| Monitoring (Sentry) | $29 |
| **Total** | **$79/mois** |

---

## 🎯 Critères de Succès

- [ ] ✅ Rollback automatique fonctionne (100% des cas)
- [ ] ✅ Notifications utilisateur envoyées dans les 5 secondes
- [ ] ✅ Warnings préventifs à 80% quota
- [ ] ✅ Retry réussit après correction du problème
- [ ] ✅ Zéro corruption de données après timeout
- [ ] ✅ Dashboard quotas accessible et précis
- [ ] ✅ Tests automatisés coverage > 80%

---

**Prochaine révision**: Fin Sprint 1, Semaine 3
**Responsable**: Dev Backend
**Validation**: Product Owner + QA
