#!/usr/bin/env python3
"""
Script de test complet pour RAG Service - PHASE 1: Embedding Engine

Usage:
    python backend/tests/run_rag_tests.py --all
    python backend/tests/run_rag_tests.py --use-case 1
    python backend/tests/run_rag_tests.py --use-case 2
    python backend/tests/run_rag_tests.py --use-case 3

Prérequis:
    - Redis running (docker-compose up -d redis)
    - PostgreSQL running pour Use Case 3 (docker-compose up -d postgres)
    - OPENAI_API_KEY configuré dans .env
"""

import asyncio
import argparse
import sys
import os
import time
from uuid import uuid4
from datetime import datetime
from pathlib import Path

# Change to backend directory to load .env correctly
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# Add parent directory to path
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.rag_service import rag_service
from app.core.config import settings

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}► {text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

def print_result(text):
    print(f"{Colors.YELLOW}   {text}{Colors.ENDC}")

# Setup DB
engine = create_async_engine(settings.database_url)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def use_case_1_embedding_cache():
    """
    Use Case 1: Test Embedding Simple (Cache Miss → Cache Hit)

    Objectif: Valider création embedding + cache Redis
    """
    print_header("USE CASE 1: EMBEDDING + CACHE REDIS")

    text = "Notre infrastructure dispose de 147 switchs Cisco et 54 VMs VMware."

    try:
        # Test 1: Cache miss
        print_section("Test 1.1: Premier appel (cache miss)")
        start = time.time()
        embedding1 = await rag_service.create_embedding(text)
        elapsed1 = time.time() - start

        print_success(f"Embedding créé: {len(embedding1)} dimensions")
        print_result(f"Preview: [{embedding1[0]:.4f}, {embedding1[1]:.4f}, {embedding1[2]:.4f}, ...]")
        print_result(f"Temps: {elapsed1*1000:.0f}ms (avec appel OpenAI)")

        # Test 2: Cache hit
        print_section("Test 1.2: Deuxième appel (cache hit)")
        start = time.time()
        embedding2 = await rag_service.create_embedding(text)
        elapsed2 = time.time() - start

        print_success("Embedding récupéré du cache")
        print_result(f"Temps: {elapsed2*1000:.0f}ms (depuis Redis)")
        print_result(f"Gain de performance: {((elapsed1-elapsed2)/elapsed1)*100:.0f}%")

        # Vérification
        assert embedding1 == embedding2, "Embeddings doivent être identiques"
        assert len(embedding1) == 1536, "Dimensions incorrectes"

        print_success("Les embeddings sont identiques (cache fonctionne)")

        return {
            "status": "✅ PASSED",
            "embedding_dimensions": len(embedding1),
            "cache_hit_speedup": f"{((elapsed1-elapsed2)/elapsed1)*100:.0f}%",
            "api_call_time_ms": f"{elapsed1*1000:.0f}",
            "cache_time_ms": f"{elapsed2*1000:.0f}"
        }

    except Exception as e:
        print_error(f"Test échoué: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "❌ FAILED", "error": str(e)}


async def use_case_2_batch_embeddings():
    """
    Use Case 2: Test Batch Embeddings (Optimisation Coûts)

    Objectif: Valider batch embeddings (1 appel API pour N textes)
    """
    print_header("USE CASE 2: BATCH EMBEDDINGS (OPTIMISATION COÛTS)")

    texts = [
        "Infrastructure: 147 switchs Cisco",
        "Virtualisation: 54 VMs VMware ESXi",
        "Stockage: SAN Fibre Channel 100 TB",
        "Réseau: Firewall Palo Alto PA-5220",
        "Monitoring: Supervision Zabbix 24/7"
    ]

    try:
        print_section(f"Test 2.1: Batch de {len(texts)} textes")
        print_info(f"Sans batch: {len(texts)} appels API")
        print_info(f"Avec batch: 1 appel API → économie de {len(texts)-1} appels")

        start = time.time()
        embeddings = await rag_service.create_embeddings_batch(texts)
        elapsed = time.time() - start

        print_success(f"{len(embeddings)} embeddings créés en 1 appel API")
        print_result(f"Temps total: {elapsed*1000:.0f}ms")
        print_result(f"Temps moyen par embedding: {(elapsed/len(embeddings))*1000:.0f}ms")

        for i, (emb, text) in enumerate(zip(embeddings, texts)):
            print_result(f"[{i}] {len(emb)} dim - {text[:40]}...")

        # Vérifications
        assert len(embeddings) == len(texts), "Nombre embeddings incorrect"
        assert all(len(e) == 1536 for e in embeddings), "Dimensions incorrectes"
        assert all(e is not None for e in embeddings), "Embeddings None trouvés"

        print_success("Batch embeddings validé")

        # Calcul économie
        estimated_individual_time = elapsed * len(texts)
        savings_pct = ((estimated_individual_time - elapsed) / estimated_individual_time) * 100

        return {
            "status": "✅ PASSED",
            "texts_count": len(texts),
            "api_calls": 1,
            "savings": f"{len(texts)-1} appels",
            "time_ms": f"{elapsed*1000:.0f}",
            "estimated_savings_pct": f"{savings_pct:.0f}%"
        }

    except Exception as e:
        print_error(f"Test échoué: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "❌ FAILED", "error": str(e)}


async def use_case_3_full_workflow():
    """
    Use Case 3: Test Ingestion Document + Recherche Sémantique

    Objectif: Valider workflow complet (chunking → embeddings → stockage → recherche)
    """
    print_header("USE CASE 3: WORKFLOW COMPLET (INGESTION + RECHERCHE)")

    # Document de test: mémoire technique
    document_content = """
Notre société possède la certification ISO 27001 pour la sécurité de l'information.
Nous gérons une infrastructure de 147 switchs Cisco et 54 machines virtuelles VMware.
Notre équipe technique comprend 12 ingénieurs certifiés (CCNP, VCP, AWS Solutions Architect).
Nous assurons une supervision 24/7 avec Zabbix et un SLA de disponibilité à 99.9%.
Nos datacenters sont certifiés Tier 3 avec redondance N+1 sur tous les équipements critiques.
    """

    doc_id = uuid4()

    try:
        async with async_session() as db:
            # 1. Ingestion du document
            print_section("Test 3.1: Ingestion du document dans pgvector")
            print_info(f"Document ID: {doc_id}")
            print_info(f"Type: past_proposal")
            print_info(f"Taille: {len(document_content)} caractères")

            start = time.time()
            chunk_count = await rag_service.ingest_document(
                db=db,
                document_id=doc_id,
                content=document_content,
                document_type="past_proposal",
                metadata={"title": "Mémoire Technique 2024", "client": "Ministère"}
            )
            elapsed_ingest = time.time() - start

            print_success(f"{chunk_count} chunks créés et stockés avec embeddings")
            print_result(f"Temps d'ingestion: {elapsed_ingest*1000:.0f}ms")

            # 2. Recherche sémantique
            print_section("Test 3.2: Recherches sémantiques")

            queries = [
                "Quelles certifications possédez-vous ?",
                "Quelle est votre infrastructure réseau ?",
                "Quel est votre niveau de supervision ?"
            ]

            all_results = []

            for query in queries:
                print_info(f"🔍 Recherche: '{query}'")

                start = time.time()
                results = await rag_service.retrieve_relevant_content(
                    db=db,
                    query=query,
                    top_k=2,
                    document_types=["past_proposal"]
                )
                elapsed_search = time.time() - start

                for i, result in enumerate(results, 1):
                    score = result['similarity_score']
                    text_preview = result['chunk_text'][:80].replace('\n', ' ')
                    print_result(f"[{i}] Score: {score:.3f} - {text_preview}...")

                print_result(f"Temps de recherche: {elapsed_search*1000:.0f}ms")

                all_results.extend(results)

            # Vérifications
            assert chunk_count > 0, "Aucun chunk créé"
            assert len(all_results) > 0, "Aucun résultat de recherche"

            # Vérifier que les scores sont cohérents
            top_scores = [r['similarity_score'] for r in all_results[:3]]
            assert all(s > 0.3 for s in top_scores), f"Scores trop faibles: {top_scores}"

            print_success("Workflow complet validé")

            return {
                "status": "✅ PASSED",
                "chunks_created": chunk_count,
                "ingestion_time_ms": f"{elapsed_ingest*1000:.0f}",
                "queries_tested": len(queries),
                "avg_similarity_score": f"{sum(r['similarity_score'] for r in all_results[:3])/3:.3f}",
                "results_found": len(all_results)
            }

    except Exception as e:
        print_error(f"Test échoué: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "❌ FAILED", "error": str(e)}


async def run_all_tests():
    """Execute tous les use cases."""
    print_header("🚀 TESTS RAG SERVICE - PHASE 1: EMBEDDING ENGINE")

    print_info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"OpenAI Model: {settings.embedding_model}")
    print_info(f"Redis URL: {settings.redis_url}")
    print_info(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'N/A'}")

    results = {}

    # Use Case 1
    results['use_case_1'] = await use_case_1_embedding_cache()

    # Use Case 2
    results['use_case_2'] = await use_case_2_batch_embeddings()

    # Use Case 3
    results['use_case_3'] = await use_case_3_full_workflow()

    # Final report
    print_header("📊 RAPPORT FINAL")

    for uc_name, uc_result in results.items():
        status = uc_result.pop('status')
        print(f"\n{Colors.BOLD}{uc_name.upper().replace('_', ' ')}:{Colors.ENDC} {status}")

        if 'error' not in uc_result:
            for key, value in uc_result.items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")

    # Summary
    passed = sum(1 for r in results.values() if '✅' in r.get('status', ''))
    total = len(results)

    print(f"\n{Colors.BOLD}Résumé:{Colors.ENDC}")
    print(f"  • Tests réussis: {passed}/{total}")
    print(f"  • Tests échoués: {total-passed}/{total}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TOUS LES TESTS SONT PASSÉS !{Colors.ENDC}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  CERTAINS TESTS ONT ÉCHOUÉ{Colors.ENDC}")
        return 1


async def run_single_test(use_case: int):
    """Execute un seul use case."""
    if use_case == 1:
        result = await use_case_1_embedding_cache()
    elif use_case == 2:
        result = await use_case_2_batch_embeddings()
    elif use_case == 3:
        result = await use_case_3_full_workflow()
    else:
        print_error(f"Use case {use_case} invalide. Choisir 1, 2 ou 3.")
        return 1

    return 0 if '✅' in result.get('status', '') else 1


def main():
    parser = argparse.ArgumentParser(
        description='Tests RAG Service - PHASE 1: Embedding Engine'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Exécuter tous les use cases'
    )
    parser.add_argument(
        '--use-case',
        type=int,
        choices=[1, 2, 3],
        help='Exécuter un use case spécifique (1, 2, ou 3)'
    )

    args = parser.parse_args()

    # Vérifier prérequis
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_key_here":
        print_error("OPENAI_API_KEY non configuré dans .env")
        print_info("Ajoutez: OPENAI_API_KEY=sk-... dans votre fichier .env")
        return 1

    if args.all:
        exit_code = asyncio.run(run_all_tests())
    elif args.use_case:
        exit_code = asyncio.run(run_single_test(args.use_case))
    else:
        parser.print_help()
        exit_code = 0

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
