#!/usr/bin/env bash

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DEPLOY_CONFIG="$PROJECT_ROOT/.deployment/config.env"

echo -e "${GREEN}=== UFC Pokedex Deployment Script ===${NC}"
echo ""

# Check if config exists
if [ ! -f "$DEPLOY_CONFIG" ]; then
    echo -e "${RED}Error: Deployment config not found at $DEPLOY_CONFIG${NC}"
    echo -e "${YELLOW}Please create .deployment/config.env from .deployment/config.env.example${NC}"
    exit 1
fi

# Load deployment configuration
source "$DEPLOY_CONFIG"

# Validate required variables
if [ -z "$SSH_HOST" ] || [ -z "$SSH_USER" ] || [ -z "$DEPLOY_PATH" ]; then
    echo -e "${RED}Error: Missing required deployment variables${NC}"
    echo "Required: SSH_HOST, SSH_USER, DEPLOY_PATH"
    exit 1
fi

# Set defaults
SSH_PORT=${SSH_PORT:-22}
SSH_KEY_PATH=${SSH_KEY_PATH:-.deployment/id_rsa}
BUILD_DIR="$FRONTEND_DIR/out"

echo -e "${YELLOW}Deployment Configuration:${NC}"
echo "  SSH Host: $SSH_HOST:$SSH_PORT"
echo "  SSH User: $SSH_USER"
echo "  Deploy Path: $DEPLOY_PATH"
echo "  Subdomain: ${SUBDOMAIN:-N/A}"
echo ""

# Step 1: Build the frontend
echo -e "${GREEN}[1/4] Building Next.js static export...${NC}"
cd "$FRONTEND_DIR"

# Set production API URL if specified
if [ -n "$PROD_API_URL" ]; then
    export NEXT_PUBLIC_API_BASE_URL="$PROD_API_URL"
    echo -e "${YELLOW}Using production API: $PROD_API_URL${NC}"
fi

# Run static build
npm run build:static

if [ ! -d "$BUILD_DIR" ]; then
    echo -e "${RED}Error: Build directory not found at $BUILD_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build complete${NC}"
echo ""

# Step 2: Test SSH connection
echo -e "${GREEN}[2/4] Testing SSH connection...${NC}"

SSH_OPTS="-i $PROJECT_ROOT/$SSH_KEY_PATH -p $SSH_PORT -o StrictHostKeyChecking=no -o ConnectTimeout=10"

# Handle encrypted SSH key
if [ -n "$SSH_KEY_PASSPHRASE" ]; then
    # Use sshpass if available, otherwise use expect
    if command -v sshpass &> /dev/null; then
        SSH_CMD="sshpass -p '$SSH_KEY_PASSPHRASE' ssh $SSH_OPTS"
        RSYNC_CMD="sshpass -p '$SSH_KEY_PASSPHRASE' rsync -e 'ssh $SSH_OPTS'"
    else
        echo -e "${YELLOW}Warning: sshpass not found. You may be prompted for SSH key passphrase.${NC}"
        SSH_CMD="ssh $SSH_OPTS"
        RSYNC_CMD="rsync -e 'ssh $SSH_OPTS'"
    fi
else
    SSH_CMD="ssh $SSH_OPTS"
    RSYNC_CMD="rsync -e 'ssh $SSH_OPTS'"
fi

# Test connection
if eval "$SSH_CMD $SSH_USER@$SSH_HOST 'echo Connection successful'" &>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}Error: Could not connect to $SSH_USER@$SSH_HOST${NC}"
    echo -e "${YELLOW}Please check your SSH credentials and ensure the server is accessible${NC}"
    exit 1
fi
echo ""

# Step 3: Create deployment directory if it doesn't exist
echo -e "${GREEN}[3/4] Preparing deployment directory...${NC}"
eval "$SSH_CMD $SSH_USER@$SSH_HOST 'mkdir -p $DEPLOY_PATH'" || {
    echo -e "${RED}Error: Could not create deployment directory${NC}"
    exit 1
}
echo -e "${GREEN}✓ Deployment directory ready${NC}"
echo ""

# Step 4: Deploy files via rsync
echo -e "${GREEN}[4/4] Deploying files to $SSH_HOST...${NC}"

# Rsync options:
# -a: archive mode (recursive, preserve permissions, etc.)
# -v: verbose
# -z: compress during transfer
# --delete: delete files on server that don't exist locally
# --exclude: exclude certain files/directories
eval "$RSYNC_CMD -avz --delete \
    --exclude='.git' \
    --exclude='.env*' \
    --exclude='node_modules' \
    $BUILD_DIR/ $SSH_USER@$SSH_HOST:$DEPLOY_PATH/" || {
    echo -e "${RED}Error: File deployment failed${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""

# Show deployment URL
if [ -n "$SUBDOMAIN" ]; then
    echo -e "${GREEN}Your site is now live at: https://$SUBDOMAIN${NC}"
else
    echo -e "${GREEN}Your site is deployed to: $DEPLOY_PATH${NC}"
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Visit your cPanel and verify the subdomain points to: $DEPLOY_PATH"
echo "  2. Test your deployed site"
echo "  3. Configure SSL certificate in cPanel (if not already done)"
