#!/bin/bash
# Ghost Audit Worker — GCE VM Setup Script
# Run this on a fresh Debian/Ubuntu VM (e2-standard-4 recommended)

set -euo pipefail

echo "=== Ghost Audit Worker Setup ==="

# System deps
sudo apt-get update && sudo apt-get install -y \
  python3 python3-venv python3-pip \
  curl git

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Codex CLI
sudo npm install -g @openai/codex
echo "Codex version: $(codex --version 2>/dev/null || echo 'installed')"

# Create audit workspace
sudo mkdir -p /var/ghost-audits
sudo mkdir -p /opt/ghost-worker
sudo chown "$(whoami):$(whoami)" /var/ghost-audits /opt/ghost-worker

# Copy worker code (assuming it's in the current directory)
cp -r . /opt/ghost-worker/

# Setup Python environment
python3 -m venv /opt/ghost-worker/venv
source /opt/ghost-worker/venv/bin/activate
pip install -r /opt/ghost-worker/requirements.txt

# Create .env file
cat > /opt/ghost-worker/.env << 'ENVEOF'
OPENAI_API_KEY=REPLACE_ME
WORKER_API_KEY=REPLACE_ME
AUDIT_DIR=/var/ghost-audits
CODEX_DISCOVERY_MODEL=o3
CODEX_VALIDATION_MODEL=o3
ENVEOF

echo "Edit /opt/ghost-worker/.env with your API keys!"

# Create systemd service
sudo tee /etc/systemd/system/ghost-worker.service > /dev/null << 'EOF'
[Unit]
Description=Ghost Audit Worker
After=network.target

[Service]
Type=simple
User=REPLACE_USER
WorkingDirectory=/opt/ghost-worker
EnvironmentFile=/opt/ghost-worker/.env
ExecStart=/opt/ghost-worker/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Update the User field
sudo sed -i "s/REPLACE_USER/$(whoami)/" /etc/systemd/system/ghost-worker.service

sudo systemctl daemon-reload
sudo systemctl enable ghost-worker

echo ""
echo "=== Setup Complete ==="
echo "1. Edit /opt/ghost-worker/.env with your API keys"
echo "2. Start the service: sudo systemctl start ghost-worker"
echo "3. Check status: sudo systemctl status ghost-worker"
echo "4. View logs: journalctl -u ghost-worker -f"
