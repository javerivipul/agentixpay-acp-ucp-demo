#!/bin/bash

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down..."

    # Kill all child processes
    pkill -P $$ 2>/dev/null

    # Force kill tsx and vite-node processes
    pkill -9 -f "tsx watch" 2>/dev/null
    pkill -9 -f "vite-node" 2>/dev/null
    pkill -9 -f concurrently 2>/dev/null

    # Stop docker containers
    docker compose down 2>/dev/null

    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Source parent .env if exists
if [ -f .env ]; then
    echo "Loading parent .env configuration..."
    set -a
    source .env
    set +a
fi

# Sync environment files - create symlinks to parent .env
echo "Syncing environment files from parent .env..."

# Create or update symlinks to parent .env for each service
for dir in demo/merchant demo/psp demo/mcp-ui-server chat-client; do
    if [ -f .env ] && [ ! -L "$dir/.env" ]; then
        # Backup existing .env if it's not a symlink
        if [ -f "$dir/.env" ] && [ ! -L "$dir/.env" ]; then
            mv "$dir/.env" "$dir/.env.backup"
        fi
        # Create symlink to parent .env
        ln -sf ../../.env "$dir/.env"
        echo "  Linked $dir/.env -> parent .env"
    fi
done

# Start PostgreSQL containers
docker compose up -d --wait
sleep 5

# Start all services
npx concurrently -n MCP,MERCHANT,PSP,CHAT -c cyan,green,yellow,blue \
    "cd demo/mcp-ui-server && npm run dev" \
    "cd demo/merchant && npm run dev" \
    "cd demo/psp && npm run dev" \
    "cd chat-client && npm run dev" &

# Wait for background process
wait
