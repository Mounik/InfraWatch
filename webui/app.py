#!/usr/bin/env python3
"""InfraWatch Web UI -- Flask app for server management"""

import json
import os
import re
import secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session,
)
import requests

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DATA_DIR = Path(os.environ.get("INFRAWATCH_DATA", "/opt/infrawatch/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SERVERS_FILE = DATA_DIR / "servers.json"

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
ALERTMANAGER_URL = os.environ.get("ALERTMANAGER_URL", "http://localhost:9093")

WEBUI_USERNAME = os.environ.get("WEBUI_USERNAME", "admin")
WEBUI_PASSWORD = os.environ.get("WEBUI_PASSWORD", "infrawatch")

TARGETS_DIR = Path(os.environ.get("PROMETHEUS_TARGETS_DIR", "/etc/prometheus/file_sd"))

HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]{0,62}$")
IP_RE = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

ALLOWED_LABEL_KEYS = {"role", "env", "region", "team", "project"}
ALLOWED_LABEL_VALUES = re.compile(r"^[a-zA-Z0-9\_\-]{1,64}$")


def load_servers():
    if SERVERS_FILE.exists():
        with open(SERVERS_FILE) as f:
            return json.load(f)
    return []


def save_servers(servers):
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)


def regenerate_targets(servers):
    targets_file = TARGETS_DIR / "node-exporter.json"
    if not targets_file.parent.exists():
        return

    targets = []
    for s in servers:
        t = {
            "targets": [f"{s['ip']}:9100"],
            "labels": {"instance": s["hostname"], **s.get("labels", {})},
        }
        targets.append(t)

    tmp_file = targets_file.with_suffix(".tmp")
    with open(tmp_file, "w") as f:
        json.dump(targets, f, indent=2)
    tmp_file.rename(targets_file)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def csrf_protect(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.pop("_csrf_token", None)
        if not token or token != request.form.get("csrf_token"):
            flash("CSRF token mismatch", "error")
            return redirect(request.url)
        return f(*args, **kwargs)

    return decorated


@app.context_processor
def inject_csrf():
    return {"csrf_token": generate_csrf_token()}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == WEBUI_USERNAME
            and request.form.get("password") == WEBUI_PASSWORD
        ):
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    servers = load_servers()
    return render_template("dashboard.html", servers=servers, count=len(servers))


@app.route("/add-server", methods=["GET", "POST"])
@login_required
@csrf_protect
def add_server():
    if request.method == "GET":
        return render_template("add-server.html")

    hostname = request.form.get("hostname", "").strip()
    ip = request.form.get("ip", "").strip()
    role = request.form.get("role", "").strip()
    env = request.form.get("env", "production").strip()

    if not HOSTNAME_RE.match(hostname):
        flash("Invalid hostname format", "error")
        return redirect(url_for("add_server"))
    if not IP_RE.match(ip):
        flash("Invalid IP address", "error")
        return redirect(url_for("add_server"))

    labels = {}
    if role:
        labels["role"] = role
    if env:
        labels["env"] = env

    servers = load_servers()
    if any(s["hostname"] == hostname for s in servers):
        flash(f"Server {hostname} already exists", "error")
        return redirect(url_for("add_server"))

    servers.append(
        {
            "hostname": hostname,
            "ip": ip,
            "labels": labels,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
    )
    save_servers(servers)
    regenerate_targets(servers)

    flash(f"Server {hostname} added successfully", "success")
    return redirect(url_for("dashboard"))


@app.route("/alerts")
@login_required
def alerts():
    try:
        r = requests.get(f"{ALERTMANAGER_URL}/api/v2/alerts", timeout=10)
        alert_data = r.json()
        firing = [a for a in alert_data if a.get("status", {}).get("state") == "firing"]
        pending = [
            a for a in alert_data if a.get("status", {}).get("state") == "pending"
        ]
        resolved = [
            a for a in alert_data if a.get("status", {}).get("state") == "suppressed"
        ]
        formatted = []
        for a in alert_data:
            formatted.append(
                {
                    "labels": a.get("labels", {}),
                    "annotations": a.get("annotations", {}),
                    "state": a.get("status", {}).get("state", "inactive"),
                    "activeAt": a.get("startsAt", "--"),
                }
            )
    except Exception:
        formatted = []
        firing = []
        pending = []
        resolved = []

    return render_template(
        "alerts.html",
        alerts=formatted,
        firing_count=len(firing),
        pending_count=len(pending),
        resolved_count=len(resolved),
    )


@app.route("/api/servers", methods=["GET", "POST"])
@login_required
def api_servers():
    if request.method == "GET":
        return jsonify(load_servers())

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    hostname = data.get("hostname", "").strip()
    ip = data.get("ip", "").strip()

    if not HOSTNAME_RE.match(hostname):
        return jsonify({"error": "Invalid hostname"}), 400
    if not IP_RE.match(ip):
        return jsonify({"error": "Invalid IP address"}), 400

    labels = {}
    for k, v in data.get("labels", {}).items():
        if k in ALLOWED_LABEL_KEYS and ALLOWED_LABEL_VALUES.match(str(v)):
            labels[k] = str(v)

    servers = load_servers()
    if any(s["hostname"] == hostname for s in servers):
        return jsonify(
            {"status": "exists", "message": "Server already registered"}
        ), 409

    servers.append(
        {
            "hostname": hostname,
            "ip": ip,
            "labels": labels,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
    )
    save_servers(servers)
    regenerate_targets(servers)

    return jsonify({"status": "created", "hostname": hostname}), 201


@app.route("/api/servers/<hostname>", methods=["DELETE"])
@login_required
def delete_server(hostname):
    servers = [s for s in load_servers() if s["hostname"] != hostname]
    save_servers(servers)
    regenerate_targets(servers)
    return jsonify({"status": "deleted"}), 200


@app.route("/api/servers/<hostname>/status")
@login_required
def server_status(hostname):
    servers = load_servers()
    server = next((s for s in servers if s["hostname"] == hostname), None)
    if not server:
        return jsonify({"error": "not found"}), 404

    try:
        r = requests.get(f"http://{server['ip']}:9100/metrics", timeout=5)
        server["status"] = "up" if r.status_code == 200 else "down"
        server["last_check"] = datetime.now(timezone.utc).isoformat()
    except Exception:
        server["status"] = "down"

    save_servers(servers)
    return jsonify({k: v for k, v in server.items() if k != "error"})


@app.route("/api/alerts")
@login_required
def get_alerts():
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/alerts", timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": "Prometheus unreachable"}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
