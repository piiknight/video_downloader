#!/bin/bash
# Deploy backend to Oracle Cloud VPS
# Usage: ./deploy.sh <server-ip>

set -e

SERVER=$1
if [ -z "$SERVER" ]; then
    echo "Usage: ./deploy.sh <server-ip>"
    exit 1
fi

echo "Deploying to $SERVER..."

# Copy backend files
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.env' \
    ./ ubuntu@$SERVER:~/video-downloader/

# Setup on server
ssh ubuntu@$SERVER << 'EOF'
cd ~/video-downloader

# Install Python if needed
sudo apt update && sudo apt install -y python3 python3-venv python3-pip ffmpeg

# Setup venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/video-downloader.service > /dev/null << 'SERVICE'
[Unit]
Description=Video Downloader API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/video-downloader
EnvironmentFile=/home/ubuntu/video-downloader/.env
ExecStart=/home/ubuntu/video-downloader/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable video-downloader
sudo systemctl restart video-downloader

echo "Backend deployed and running!"
EOF
