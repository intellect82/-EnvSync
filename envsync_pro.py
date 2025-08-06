import os
import platform
import subprocess
import json
import argparse
from flask import Flask, jsonify

# Python 3.8+ way to list installed packages
try:
    from importlib import metadata  # Python 3.8+
except ImportError:
    import importlib_metadata as metadata  # fallback

app = Flask(__name__)
report = {}

def scan_environment():
    """Collect environment details and package info"""
    global report

    # --- OS Info ---
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
    }

    # --- Python Info ---
    py_packages = {}
    for dist in metadata.distributions():
        py_packages[dist.metadata['Name'].lower()] = dist.version

    python_info = {
        "version": platform.python_version(),
        "executable": os.sys.executable,
        "packages": py_packages
    }

    # --- Java Info ---
    try:
        java_version = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT).decode()
    except Exception:
        java_version = "Java not found"

    try:
        javac_version = subprocess.check_output(["javac", "-version"], stderr=subprocess.STDOUT).decode().strip()
    except Exception:
        javac_version = "javac not found"

    java_info = {
        "version": java_version,
        "javac_version": javac_version
    }

    # --- Node.js Info ---
    try:
        node_version = subprocess.check_output(["node", "-v"]).decode().strip()
    except Exception:
        node_version = "Node not found"

    try:
        npm_version = subprocess.check_output(["npm", "-v"]).decode().strip()
    except Exception:
        npm_version = "NPM not found"

    try:
        global_packages = subprocess.check_output(["npm", "list", "-g", "--depth=0"]).decode()
    except Exception:
        global_packages = "No global packages or npm not found"

    node_info = {
        "version": node_version,
        "npm_version": npm_version,
        "global_packages": global_packages
    }

    # --- Conflict Detection (MVP Demo) ---
    conflicts = {
        "python": [],
        "node": ["ejs missing (required ^3.1.10)", "nodemailer missing (required ^6.9.13)"],
        "java": []
    }

    report = {
        "os": os_info,
        "python": python_info,
        "java": java_info,
        "node": node_info,
        "conflicts": conflicts
    }

    # Save JSON & HTML reports for local demo (optional)
    with open("envsync_report.json", "w") as f:
        json.dump(report, f, indent=4)

    return report

@app.route("/api/report")
def api_report():
    """Return latest environment scan as JSON"""
    return jsonify(report)

def run_dashboard():
    scan_environment()  # initial scan
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EnvSync Pro MVP")
    parser.add_argument("--dashboard", action="store_true", help="Run Flask dashboard")
    args = parser.parse_args()

    if args.dashboard:
        run_dashboard()
    else:
        data = scan_environment()
        print(json.dumps(data, indent=4))
