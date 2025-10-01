#!/usr/bin/env python3
"""
Script de vérification des prérequis pour les tests RAG.

Usage:
    python backend/tests/check_prerequisites.py
"""

import sys
import os
from pathlib import Path

# Change to backend directory to load .env correctly
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# Add parent directory to path
sys.path.insert(0, str(backend_dir))

import redis as redis_sync
from sqlalchemy import create_engine, text

from app.core.config import settings

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")

def check_ok(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def check_fail(text):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def check_warn(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def check_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")


def check_openai_api_key():
    """Vérifier OPENAI_API_KEY."""
    print_header("1. OpenAI API Key")

    if not settings.openai_api_key:
        check_fail("OPENAI_API_KEY non configuré")
        check_info("Ajoutez OPENAI_API_KEY=sk-... dans .env")
        return False

    if settings.openai_api_key == "sk-your-openai-key-here":
        check_fail("OPENAI_API_KEY est la valeur par défaut")
        check_info("Remplacez par votre vraie clé OpenAI")
        return False

    if not settings.openai_api_key.startswith("sk-"):
        check_warn("Format de clé OpenAI inhabituel (devrait commencer par 'sk-')")

    check_ok(f"OPENAI_API_KEY configuré ({settings.openai_api_key[:15]}...)")
    return True


def check_redis():
    """Vérifier connexion Redis."""
    print_header("2. Redis")

    try:
        client = redis_sync.from_url(settings.redis_url)
        response = client.ping()

        if response:
            check_ok(f"Redis accessible ({settings.redis_url})")

            # Test set/get
            test_key = "test:rag_prerequisites"
            client.set(test_key, "OK", ex=10)
            value = client.get(test_key)

            if value == b"OK":
                check_ok("Redis read/write fonctionne")

            client.delete(test_key)
            return True
        else:
            check_fail("Redis ping échoué")
            return False

    except Exception as e:
        check_fail(f"Redis inaccessible: {e}")
        check_info("Démarrez Redis: docker-compose up -d redis")
        return False


def check_postgres():
    """Vérifier connexion PostgreSQL."""
    print_header("3. PostgreSQL")

    try:
        # Convertir URL async vers sync pour test
        sync_url = settings.database_url.replace("+asyncpg", "")
        if "asyncpg" in sync_url:
            sync_url = sync_url.replace("asyncpg", "psycopg2")

        engine = create_engine(sync_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()

            if row and row[0] == 1:
                check_ok(f"PostgreSQL accessible ({settings.database_url.split('@')[1] if '@' in settings.database_url else 'N/A'})")

                # Vérifier pgvector
                try:
                    result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
                    row = result.fetchone()

                    if row:
                        check_ok("Extension pgvector installée")
                    else:
                        check_warn("Extension pgvector non trouvée")
                        check_info("Exécutez: CREATE EXTENSION vector;")

                except Exception as e:
                    check_warn(f"Impossible de vérifier pgvector: {e}")

                # Vérifier table document_embeddings
                try:
                    result = conn.execute(text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = 'document_embeddings'"
                    ))
                    row = result.fetchone()

                    if row:
                        check_ok("Table document_embeddings existe")
                    else:
                        check_warn("Table document_embeddings non trouvée")
                        check_info("Exécutez: alembic upgrade head")

                except Exception as e:
                    check_warn(f"Impossible de vérifier tables: {e}")

                return True

    except Exception as e:
        check_fail(f"PostgreSQL inaccessible: {e}")
        check_info("Démarrez PostgreSQL: docker-compose up -d postgres")
        check_info("Appliquez migrations: alembic upgrade head")
        return False


def check_embedding_model():
    """Vérifier configuration modèle embedding."""
    print_header("4. Configuration Embedding")

    model = settings.embedding_model
    check_ok(f"Modèle: {model}")

    if "text-embedding-3-small" in model:
        check_info("Dimensions: 1536")
        check_info("Coût: ~$0.01 / 1M tokens")
    elif "text-embedding-3-large" in model:
        check_info("Dimensions: 3072")
        check_info("Coût: ~$0.13 / 1M tokens")
    else:
        check_warn(f"Modèle non reconnu: {model}")

    return True


def check_env_file():
    """Vérifier fichier .env."""
    print_header("0. Fichier .env")

    env_path = Path(__file__).parent.parent / ".env"

    if env_path.exists():
        check_ok(f".env trouvé: {env_path}")
        return True
    else:
        check_fail(f".env non trouvé: {env_path}")
        check_info("Copiez .env.example vers .env et configurez les valeurs")
        return False


def main():
    """Main execution."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'🔍 VÉRIFICATION DES PRÉREQUIS - TESTS RAG SERVICE'.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")

    checks = [
        ("Fichier .env", check_env_file),
        ("OpenAI API Key", check_openai_api_key),
        ("Redis", check_redis),
        ("PostgreSQL + pgvector", check_postgres),
        ("Configuration Embedding", check_embedding_model),
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            check_fail(f"Erreur lors de la vérification '{name}': {e}")
            results.append((name, False))

    # Summary
    print_header("📊 RÉSUMÉ")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}✅{Colors.ENDC}" if result else f"{Colors.RED}❌{Colors.ENDC}"
        print(f"  {status} {name}")

    print(f"\n{Colors.BOLD}Score: {passed}/{total} vérifications réussies{Colors.ENDC}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Tous les prérequis sont OK !{Colors.ENDC}")
        print(f"{Colors.GREEN}Vous pouvez exécuter: python backend/tests/run_rag_tests.py --all{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Certains prérequis manquants{Colors.ENDC}")
        print(f"{Colors.YELLOW}Corrigez les problèmes ci-dessus avant de lancer les tests{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
