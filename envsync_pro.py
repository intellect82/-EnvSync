import os
import platform
import subprocess
import json
import argparse
from flask import Flask, jsonify

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata

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
    py_packages = {dist.metadata['Name'].lower(): dist.version
                   for dist in metadata.distributions()}

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

    java_info = {"version": java_version, "javac_version": javac_version}

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

    with open("envsync_report.json", "w") as f:
        json.dump(report, f, indent=4)

    return report

@app.route("/api/report")
def api_report():
    return jsonify(report)

@app.route("/")
def dashboard():
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EnvSync Pro Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; background:#f4f6f8; margin:0; }}
            header {{ background:#4CAF50; color:white; padding:20px; text-align:center; font-size:28px; }}
            .container {{ width:90%; max-width:1200px; margin:30px auto; }}
            pre {{ background:#f4f4f4; padding:10px; border-radius:5px; overflow-x:auto; }}
        </style>
    </head>
    <body>
        <header>EnvSync Pro Dashboard (Auto-refresh every 30s)</header>
        <div class="container">
            <pre id="json">Loading environment...</pre>
        </div>
        <script>
            async function fetchReport() {{
                const res = await fetch('/api/report');
                const data = await res.json();
                document.getElementById('json').textContent = JSON.stringify(data, null, 2);
            }}
            fetchReport();
            setInterval(fetchReport, 30000);
        </script>
    </body>
    </html>
    """

def run_dashboard():
    scan_environment()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EnvSync Pro MVP")
    parser.add_argument("--dashboard", action="store_true", help="Run Flask dashboard")
    args = parser.parse_args()

    if args.dashboard:
        run_dashboard()
    else:
        data = scan_environment()
        print(json.dumps(data, indent=4))
