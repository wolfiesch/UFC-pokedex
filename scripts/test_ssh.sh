#!/usr/bin/env bash

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_CONFIG="$PROJECT_ROOT/.deployment/config.env"

echo -e "${GREEN}=== SSH Connection Test ===${NC}"
echo ""

if [ ! -f "$DEPLOY_CONFIG" ]; then
    echo -e "${RED}Error: .deployment/config.env not found${NC}"
    echo -e "${YELLOW}Run: make deploy-config${NC}"
    exit 1
fi

source "$DEPLOY_CONFIG"

if [ -z "$SSH_HOST" ] || [ -z "$SSH_USER" ]; then
    echo -e "${RED}Error: SSH_HOST and SSH_USER must be set in config.env${NC}"
    exit 1
fi

SSH_PORT=${SSH_PORT:-22}
SSH_KEY_PATH=${SSH_KEY_PATH:-.deployment/id_rsa}

echo -e "${YELLOW}Testing connection to:${NC}"
echo "  Host: $SSH_HOST:$SSH_PORT"
echo "  User: $SSH_USER"
echo "  Key:  $SSH_KEY_PATH"
echo ""

SSH_OPTS="-i $PROJECT_ROOT/$SSH_KEY_PATH -p $SSH_PORT -o ConnectTimeout=10"

echo -e "${YELLOW}Attempting SSH connection...${NC}"
echo "(You may be prompted for your SSH key passphrase)"
echo ""

if ssh $SSH_OPTS "$SSH_USER@$SSH_HOST" "echo '✓ Connection successful!'; pwd; whoami"; then
    echo ""
    echo -e "${GREEN}✅ SSH connection works!${NC}"
    echo ""
    echo "You're ready to deploy. Run:"
    echo -e "  ${YELLOW}make deploy${NC}"
else
    echo ""
    echo -e "${RED}❌ SSH connection failed${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Verify SSH is enabled in cPanel"
    echo "  2. Check username and hostname are correct"
    echo "  3. Try different port (22 or 2222)"
    echo "  4. Ensure public key is added to cPanel → SSH Access → Manage SSH Keys"
    echo "  5. Contact Namecheap support if SSH is not available"
    exit 1
fi
