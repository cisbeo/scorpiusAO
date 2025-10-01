#!/bin/bash
# Script de lancement des tests RAG Service - PHASE 1

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}              🧪 TESTS RAG SERVICE - PHASE 1: EMBEDDING ENGINE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier si on est dans le bon répertoire
if [ ! -f "backend/docker-compose.yml" ]; then
    echo -e "${RED}❌ Erreur: backend/docker-compose.yml non trouvé${NC}"
    echo -e "${YELLOW}   Exécutez ce script depuis la racine du projet (ScorpiusAO)${NC}"
    exit 1
fi

# Fonction pour vérifier si un service Docker est running
check_service() {
    service_name=$1
    if docker-compose -f backend/docker-compose.yml ps | grep -q "$service_name.*Up"; then
        echo -e "${GREEN}✅ $service_name est démarré${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $service_name n'est pas démarré${NC}"
        return 1
    fi
}

# Étape 1: Vérifier et démarrer l'infrastructure
echo -e "${BLUE}📦 Étape 1: Vérification de l'infrastructure${NC}"
echo ""

redis_running=false
postgres_running=false

if check_service "redis"; then
    redis_running=true
fi

if check_service "postgres"; then
    postgres_running=true
fi

if [ "$redis_running" = false ] || [ "$postgres_running" = false ]; then
    echo ""
    echo -e "${YELLOW}Certains services ne sont pas démarrés.${NC}"
    read -p "Voulez-vous les démarrer maintenant? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Démarrage des services...${NC}"
        docker-compose -f backend/docker-compose.yml up -d redis postgres

        # Attendre que les services soient prêts
        echo -e "${BLUE}Attente du démarrage (5 secondes)...${NC}"
        sleep 5

        echo -e "${GREEN}✅ Services démarrés${NC}"
    else
        echo -e "${RED}❌ Tests annulés - services requis non démarrés${NC}"
        exit 1
    fi
fi

echo ""

# Étape 2: Vérifier les prérequis
echo -e "${BLUE}🔍 Étape 2: Vérification des prérequis${NC}"
echo ""

if ! python3 backend/tests/check_prerequisites.py; then
    echo ""
    echo -e "${RED}❌ Prérequis non satisfaits${NC}"
    echo -e "${YELLOW}   Corrigez les problèmes ci-dessus avant de continuer${NC}"
    exit 1
fi

echo ""

# Étape 3: Exécuter les tests
echo -e "${BLUE}🚀 Étape 3: Exécution des tests${NC}"
echo ""

# Parser les arguments
TEST_ARGS="--all"

if [ "$1" = "--use-case" ] && [ -n "$2" ]; then
    TEST_ARGS="--use-case $2"
    echo -e "${YELLOW}Exécution du Use Case $2 uniquement${NC}"
elif [ "$1" = "--help" ]; then
    echo "Usage: ./test-rag.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --use-case 1    Exécuter Use Case 1 uniquement (Embedding + Cache)"
    echo "  --use-case 2    Exécuter Use Case 2 uniquement (Batch Embeddings)"
    echo "  --use-case 3    Exécuter Use Case 3 uniquement (Workflow complet)"
    echo "  --help          Afficher cette aide"
    echo ""
    echo "Par défaut: Exécute tous les use cases"
    exit 0
else
    echo -e "${YELLOW}Exécution de tous les Use Cases${NC}"
fi

echo ""

# Exécuter les tests
python3 backend/tests/run_rag_tests.py $TEST_ARGS

# Capturer le code de sortie
EXIT_CODE=$?

echo ""

# Message final
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}                          🎉 TOUS LES TESTS SONT PASSÉS !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}                          ⚠️  CERTAINS TESTS ONT ÉCHOUÉ${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
fi

exit $EXIT_CODE
