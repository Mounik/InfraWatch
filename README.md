# InfraWatch 📊

**Production-ready monitoring stack — deploy agents, dashboards & alerts in minutes**

InfraWatch is a complete, opinionated monitoring solution that deploys to your infrastructure in one command. Node Exporter on every server, Prometheus for metrics, Grafana for dashboards, Alertmanager for notifications.

```bash
# Deploy monitoring to a new server
ansible-playbook -i inventory/hosts.yml playbooks/deploy-agent.yml --limit newserver

# Add server via web UI
# http://localhost:8080 → "Add Server" → Enter IP → Done

# View dashboards
open http://grafana.localhost
```

## 🎯 Features

- **One-command deployment** — Ansible playbook deploys full stack
- **Agent auto-discovery** — New servers appear in Grafana automatically
- **Pre-built dashboards** — CPU, RAM, disk, network, Docker, Nginx, SSL expiry
- **Smart alerts** — Discord, Telegram, email, webhook — no alert fatigue
- **Web UI** — Simple interface to add/remove servers, view status
- **SSL monitoring** — Track certificate expiry across all your domains
- **Log aggregation** — Optional Loki integration for logs
- **Multi-tenant** — Separate teams/projects with label-based filtering

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    InfraWatch Server                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Grafana    │  │  Prometheus │  │  Alertmanager   │  │
│  │  :3000      │  │  :9090      │  │  :9093          │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐                        │
│  │    Loki     │  │   Web UI    │                        │
│  │  :3100      │  │  :8080      │                        │
│  └─────────────┘  └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────┴────┐       ┌────┴────┐       ┌────┴────┐
    │ Server  │       │ Server  │       │ Server  │
    │NodeExp  │       │NodeExp  │       │NodeExp  │
    │:9100    │       │:9100    │       │:9100    │
    └─────────┘       └─────────┘       └─────────┘
```

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/Mounik/InfraWatch.git
cd InfraWatch

# 2. Configure your servers
cp inventory/hosts.yml.example inventory/hosts.yml
# Edit hosts.yml with your server IPs

# 3. Deploy everything
ansible-playbook -i inventory/hosts.yml playbooks/deploy-stack.yml

# 4. Access dashboards
# Grafana: http://your-server:3000 (admin/infrawatch)
# Web UI: http://your-server:8080
```

## 📋 Pre-built Dashboards

| Dashboard | Metrics | Alerts |
|-----------|---------|--------|
| **Node Overview** | CPU, RAM, disk, uptime | High CPU, low disk, high load |
| **Docker Containers** | Container stats, resource usage | Container down, OOM |
| **Nginx** | Requests, latency, errors | 5xx spikes, high latency |
| **SSL Certificates** | Days until expiry | Cert expires < 30 days |
| **Network** | Bandwidth, connections, errors | DDoS detection |
| **PostgreSQL** | Queries, connections, slow queries | Connection limit |

## 🔔 Alert Channels

Configure in `config/alertmanager.yml`:

```yaml
receivers:
  - name: 'discord'
    discord_configs:
      - webhook_url: 'YOUR_WEBHOOK_URL'
        
  - name: 'telegram'
    telegram_configs:
      - api_url: 'https://api.telegram.org'
        bot_token: 'YOUR_BOT_TOKEN'
        chat_id: 'YOUR_CHAT_ID'
        
  - name: 'email'
    email_configs:
      - to: 'ops@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.gmail.com:587'
```

## ⚙️ Configuration

### inventory/hosts.yml

```yaml
all:
  children:
    monitoring:
      hosts:
        monitor01:
          ansible_host: 192.168.1.10
          
    agents:
      hosts:
        web01:
          ansible_host: 192.168.1.20
          labels:
            role: webserver
            env: production
            
        db01:
          ansible_host: 192.168.1.21
          labels:
            role: database
            env: production
```

### config/prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'node-exporter'
    file_sd_configs:
      - files:
          - /etc/prometheus/targets/node-exporter.json
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
```

## 🔧 Web UI

Simple Flask/FastAPI web interface:

- **Dashboard** — overview of all monitored servers
- **Add Server** — enter IP, auto-detect OS, deploy agent
- **Remove Server** — clean removal from monitoring
- **Alerts** — view active alerts, silence noisy ones
- **Settings** — configure notification channels

```bash
# Run web UI
python -m webui

# Or with Docker
docker run -p 8080:8080 -v /opt/infrawatch:/data mounik/infrawatch-web
```

## 📊 Example Screenshots

*Node Overview Dashboard*
- CPU usage graph (last 1h, 6h, 24h, 7d)
- Memory usage with available RAM
- Disk usage with mount points
- Network I/O
- Top processes by CPU/Memory

*SSL Certificate Dashboard*
- Table of all monitored domains
- Days until expiry (green/yellow/red)
- Issuer, SANs, fingerprint
- Auto-refresh every hour

## 🧪 Testing

```bash
# Test with Docker Compose
docker-compose -f tests/docker-compose.yml up

# Run Ansible in check mode
ansible-playbook -i inventory/hosts.yml playbooks/deploy-stack.yml --check

# Validate Prometheus config
docker run --rm -v $(pwd)/config:/config prom/prometheus:latest \
  promtool check config /config/prometheus.yml
```

## 📁 Project Structure

```
InfraWatch/
├── README.md
├── ansible.cfg
├── requirements.txt
├── inventory/
│   ├── hosts.yml              # Your servers
│   └── hosts.yml.example      # Template
├── playbooks/
│   ├── deploy-stack.yml       # Full deployment
│   ├── deploy-agent.yml       # Agent only
│   ├── deploy-monitoring.yml  # Server stack only
│   └── update-dashboards.yml  # Update Grafana dashboards
├── roles/
│   ├── node-exporter/         # Agent installation
│   ├── prometheus/              # Prometheus server
│   ├── grafana/                 # Grafana with dashboards
│   ├── alertmanager/            # Alert routing
│   ├── loki/                    # Log aggregation (optional)
│   └── ssl-exporter/            # SSL certificate monitoring
├── config/
│   ├── prometheus.yml           # Prometheus config
│   ├── alertmanager.yml         # Alertmanager config
│   ├── grafana.ini              # Grafana settings
│   └── dashboards/              # JSON dashboard exports
│       ├── node-overview.json
│       ├── docker-containers.json
│       ├── nginx.json
│       └── ssl-certificates.json
├── rules/
│   └── alert-rules.yml          # Prometheus alerting rules
├── webui/
│   ├── app.py                   # Flask/FastAPI app
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── add-server.html
│   │   └── alerts.html
│   └── static/
├── scripts/
│   ├── install-agent.sh         # Bootstrap agent
│   ├── generate-dashboards.py   # Generate dashboards from templates
│   └── ssl-check.sh             # Standalone SSL checker
└── tests/
    ├── docker-compose.yml
    └── test-deployment.yml
```

## 🤝 Use Cases

- **Freelance sysadmin** — Deploy monitoring for clients, bill monthly
- **DevOps teams** — Centralized visibility across dev/staging/prod
- **Security teams** — Detect anomalies, track SSL expiry
- **Compliance** — Audit logs, retention policies

## 💰 Pricing Model (Freelance)

| Service | Price | Includes |
|---------|-------|----------|
| **Setup** | €500-1000 | Install InfraWatch, configure dashboards |
| **Per server/month** | €10-50 | Monitoring, alerting, 30-day retention |
| **On-call** | €200/month | 24h response to alerts |
| **Custom dashboards** | €100-300 | Application-specific metrics |

**Example:** 10 servers = €500 setup + €200/month = €2900/year recurring

## 📄 License

MIT License — use it, sell it, deploy it.

---

Built by [Mounik](https://github.com/Mounik) — DevSecOps Engineer | [SecurePipe](https://github.com/Mounik/SecurePipe) | [HardenLinux](https://github.com/Mounik/HardenLinux) | [docker-stacks](https://github.com/Mounik/docker-stacks) | [devops-toolkit](https://github.com/Mounik/devops-toolkit)