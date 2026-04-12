#!/bin/bash
# InfraWatch Agent Bootstrap Script
# Run on target server to install Node Exporter

set -e

NODE_EXPORTER_VERSION="1.7.0"
ARCH="amd64"

echo "=== InfraWatch Agent Bootstrap ==="

# Create user
sudo useradd --no-create-home --shell /usr/sbin/nologin node_exporter 2>/dev/null || true

# Download
cd /tmp
curl -L -o node_exporter.tar.gz "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz"
tar xzf node_exporter.tar.gz

# Install
sudo cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}/node_exporter" /usr/local/bin/
sudo chmod +x /usr/local/bin/node_exporter

# Systemd service
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter

echo "=== Node Exporter installed on port 9100 ==="