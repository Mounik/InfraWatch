#!/usr/bin/env python3
"""InfraWatch Web UI — Flask app for server management"""

import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-prod')

DATA_DIR = Path(os.environ.get('INFRAWATCH_DATA', '/opt/infrawatch/data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SERVERS_FILE = DATA_DIR / 'servers.json'

PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL', 'http://localhost:9090')

def load_servers():
    if SERVERS_FILE.exists():
        with open(SERVERS_FILE) as f:
            return json.load(f)
    return []

def save_servers(servers):
    with open(SERVERS_FILE, 'w') as f:
        json.dump(servers, f, indent=2)

@app.route('/')
def dashboard():
    servers = load_servers()
    return render_template('dashboard.html', servers=servers, count=len(servers))

@app.route('/api/servers', methods=['GET', 'POST'])
def api_servers():
    if request.method == 'GET':
        return jsonify(load_servers())
    
    data = request.json
    servers = load_servers()
    
    # Check if exists
    if any(s['hostname'] == data['hostname'] for s in servers):
        return jsonify({'status': 'exists', 'message': 'Server already registered'}), 409
    
    servers.append({
        'hostname': data['hostname'],
        'ip': data['ip'],
        'labels': data.get('labels', {}),
        'added_at': datetime.utcnow().isoformat(),
        'status': 'pending'
    })
    save_servers(servers)
    
    # Regenerate Prometheus targets
    regenerate_targets(servers)
    
    return jsonify({'status': 'created', 'hostname': data['hostname']}), 201

@app.route('/api/servers/<hostname>', methods=['DELETE'])
def delete_server(hostname):
    servers = [s for s in load_servers() if s['hostname'] != hostname]
    save_servers(servers)
    regenerate_targets(servers)
    return jsonify({'status': 'deleted'}), 200

@app.route('/api/servers/<hostname>/status')
def server_status(hostname):
    """Check if node_exporter is responding."""
    servers = load_servers()
    server = next((s for s in servers if s['hostname'] == hostname), None)
    if not server:
        return jsonify({'error': 'not found'}), 404
    
    try:
        r = requests.get(f"http://{server['ip']}:9100/metrics", timeout=5)
        server['status'] = 'up' if r.status_code == 200 else 'down'
        server['last_check'] = datetime.utcnow().isoformat()
    except Exception as e:
        server['status'] = 'down'
        server['error'] = str(e)
    
    save_servers(servers)
    return jsonify(server)

@app.route('/api/alerts')
def get_alerts():
    """Fetch alerts from Prometheus Alertmanager."""
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/alerts", timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def regenerate_targets(servers):
    """Regenerate Prometheus file_sd targets."""
    targets_file = Path('/etc/prometheus/file_sd/node-exporter.json')
    if not targets_file.parent.exists():
        return  # Not running on monitoring server
    
    targets = []
    for s in servers:
        t = {
            "targets": [f"{s['ip']}:9100"],
            "labels": {"instance": s['hostname'], **s.get('labels', {})}
        }
        targets.append(t)
    
    with open(targets_file, 'w') as f:
        json.dump(targets, f, indent=2)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)