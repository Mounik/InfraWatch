#!/usr/bin/env python3
"""Generate Grafana dashboard JSON from template definitions."""

import json
import sys
from pathlib import Path

DASHBOARDS_DIR = Path(__file__).resolve().parent.parent / "config" / "dashboards"

TEMPLATES = {
    "node-overview": {
        "title": "Node Overview",
        "tags": ["infrawatch", "node", "system"],
        "panels": [
            {
                "title": "CPU Usage",
                "type": "stat",
                "expr": '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                "unit": "percent",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
            },
            {
                "title": "Memory Usage",
                "type": "stat",
                "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
                "unit": "percent",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
            },
            {
                "title": "Disk Usage",
                "type": "table",
                "expr": "node_filesystem_avail_bytes / node_filesystem_size_bytes",
                "unit": "percentunit",
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
            },
            {
                "title": "Network I/O",
                "type": "timeseries",
                "expr": 'rate(node_network_receive_bytes_total{device!="lo"}[5m])',
                "unit": "Bps",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
            },
            {
                "title": "Load Average",
                "type": "timeseries",
                "expr": "node_load1",
                "unit": "none",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
            },
        ],
    }
}


def build_panel(panel_def, panel_id):
    p = {
        "id": panel_id,
        "title": panel_def["title"],
        "type": panel_def["type"],
        "targets": [{"expr": panel_def["expr"], "legendFormat": "{{instance}}"}],
        "gridPos": panel_def["gridPos"],
    }
    if panel_def["type"] in ("stat", "timeseries", "gauge"):
        p["fieldConfig"] = {
            "defaults": {
                "unit": panel_def.get("unit", "none"),
                "thresholds": {
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 70, "color": "yellow"},
                        {"value": 90, "color": "red"},
                    ]
                },
                "custom": {"fillOpacity": 10},
            }
        }
    if panel_def["type"] == "table":
        p["targets"][0]["format"] = "table"
        p["fieldConfig"] = {
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Value"},
                    "properties": [
                        {"id": "unit", "value": panel_def.get("unit", "none")}
                    ],
                }
            ]
        }
    return p


def generate_dashboard(name, template):
    panels = [build_panel(p, i + 1) for i, p in enumerate(template["panels"])]
    dashboard = {
        "dashboard": {
            "id": None,
            "title": template["title"],
            "tags": template["tags"],
            "timezone": "browser",
            "schemaVersion": 36,
            "refresh": "30s",
            "panels": panels,
            "time": {"from": "now-1h", "to": "now"},
            "templating": {
                "list": [
                    {
                        "name": "instance",
                        "type": "query",
                        "query": f'label_values(up{{job="{name}"}}, instance)',
                    }
                ]
            },
        }
    }
    return dashboard


def main():
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    for name, template in TEMPLATES.items():
        dashboard = generate_dashboard(name, template)
        output_path = DASHBOARDS_DIR / f"{name}.json"
        with open(output_path, "w") as f:
            json.dump(dashboard, f, indent=2)
        print(f"Generated {output_path}")

    print(f"Done. {len(TEMPLATES)} dashboards generated.")


if __name__ == "__main__":
    main()
