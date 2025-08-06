#!/usr/bin/env python3
"""
EnvSync Pro - Unified MVP (Cloud-friendly)
Features:
1. One-click environment scan (Python, Node.js, Java)
2. Generates JSON + HTML reports
3. Generates Dockerfile & optionally builds Docker image
4. Live Flask dashboard for VCs & Developers
"""

import sys, os, json, platform, subprocess, argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from flask import Flask, render_template_string, jsonify

# Modern Python package listing
try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # for Python <3.8

app = Flask(__name__)
report = {}

# ------------------ Core Scanning ------------------
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"Error: {e}"

def scan_environment():
    return {
        'os': {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine()
        },
        'python': {
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "packages": {dist.metadata['Name'].lower(): dist.version for dist in metadata.distributions()}
        },
        'java': {
            "version": run_command("java -version"),
            "javac_version": run_command("javac -version")
        },
        'node': {
            "version": run_command("node -v"),
            "npm_version": run_command("npm -v"),
            "global_packages": run_command("npm list -g --depth=0")
        }
    }

# ------------------ Dependency Parsing ------------------
def parse_requirements(filename="requirements.txt"):
    if not Path(filename).exists(): return {}
    deps = {}
    for line in Path(filename).read_text().splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        if "==" in line:
            pkg, ver = line.split("==",1)
            deps[pkg.lower()] = ver
        else:
            deps[line.lower()] = None
    return deps

def parse_package_json(filename="package.json"):
    if not Path(filename).exists(): return {}
    return json.loads(Path(filename).read_text()).get("dependencies", {})

def parse_pom_xml(filename="pom.xml"):
    if not Path(filename).exists(): return {}
    deps = {}
    tree = ET.parse(filename)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    for dep in root.findall(".//m:dependency", ns):
        artifact = dep.find("m:artifactId", ns).text
        version_tag = dep.find("m:version", ns)
        deps[artifact] = version_tag.text if version_tag is not None else None
    return deps

# ------------------ Conflict Detection ------------------
def detect_conflicts(env_report):
    conflicts = {"python":[], "node":[], "java":[]}
    py_reqs = parse_requirements()
    for pkg, req_ver in py_reqs.items():
        installed_ver = env_report["python"]["packages"].get(pkg)
        if installed_ver is None:
            conflicts["python"].append(f"{pkg} missing (required {req_ver})")
        elif req_ver and installed_ver != req_ver:
            conflicts["python"].append(f"{pkg} version mismatch: required {req_ver}, found {installed_ver}")

    node_reqs = parse_package_json()
    for pkg, req_ver in node_reqs.items():
        if pkg not in env_report["node"]["global_packages"]:
            conflicts["node"].append(f"{pkg} missing (required {req_ver})")

    java_reqs = parse_pom_xml()
    for artifact, req_ver in java_reqs.items():
        conflicts["java"].append(f"{artifact} requires {req_ver} (manual check)")
    return conflicts

# ------------------ Report Generators ------------------
def save_json(report, filename="envsync_report.json"):
    Path(filename).write_text(json.dumps(report, indent=4))
    print(f"[✓] JSON report saved to {filename}")

def save_html(report, filename="envsync_report.html"):
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EnvSync Pro Report</title>
<style>
body{{font-family:Arial;background:#f4f6f8;color:#333}}
header{{background:#4CAF50;color:white;padding:20px;text-align:center;font-size:28px}}
.container{{width:90%;max-width:1200px;margin:30px auto}}
.card{{background:white;padding:20px;border-radius:8px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
.conflict{{background:#fff4f4;border-left:6px solid #f44336;padding:5px 10px;margin:5px 0}}
.no-conflict{{background:#e8f5e9;border-left:6px solid #4CAF50;padding:5px 10px;margin:5px 0}}
pre{{background:#f4f4f4;padding:10px;border-radius:5px;overflow-x:auto}}
</style></head>
<body>
<header>EnvSync Pro Report</header>
<div class="container">
<div class="card"><h2>System Info</h2><ul>
{''.join(f"<li><b>{k.capitalize()}</b>: {v}</li>" for k,v in report['os'].items())}
</ul></div>
<div class="card"><h2>Python</h2><p><b>Version:</b> {report['python']['version']}</p>
<p><b>Executable:</b> {report['python']['executable']}</p></div>
<div class="card"><h2>Node.js</h2><p><b>Node:</b> {report['node']['version']}</p>
<p><b>NPM:</b> {report['node']['npm_version']}</p></div>
<div class="card"><h2>Java</h2><pre>{report['java']['version']}</pre></div>
<div class="card"><h2>Dependency Conflicts</h2>"""
    for lang, issues in report.get("conflicts", {}).items():
        html += f"<h3>{lang.capitalize()}</h3>"
        if issues:
            html += ''.join(f"<div class='conflict'>{issue}</div>" for issue in issues)
        else:
            html += "<div class='no-conflict'>No conflicts detected</div>"
    html += "</div></div></body></html>"
    Path(filename).write_text(html, encoding="utf-8")
    print(f"[✓] HTML report saved to {filename}")

# ------------------ Dockerfile Generator ------------------
def generate_dockerfile(report, filename="Dockerfile"):
    node_ver = report["node"]["version"].lstrip("v") if report["node"]["version"] else "18"
    dockerfile_content = f"""# Auto-generated by EnvSync Pro
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \\
    python3-pip python3-venv openjdk-17-jdk curl gnupg git \\
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://deb.nodesource.com/setup_{node_ver.split('.')[0]}.x | bash - && \\
    apt-get install -y nodejs
WORKDIR /app
COPY requirements.txt* ./
COPY package.json* package-lock.json* ./
COPY pom.xml* ./
RUN if [ -f requirements.txt ]; then pip3 install -r requirements.txt || true; fi
RUN if [ -f package.json ]; then npm install || true; fi
CMD ["bash"]
"""
    Path(filename).write_text(dockerfile_content)
    print(f"[✓] Dockerfile generated: {filename}")

# ------------------ Flask Dashboard ------------------
TEMPLATE = """<html><head><title>EnvSync Pro</title>
<meta http-equiv="refresh" content="30"></head>
<body><h1>EnvSync Pro Dashboard</h1>
<pre id="json">{{ report|tojson(indent=2) }}</pre>
</body></html>"""

@app.route("/")
def dashboard(): return render_template_string(TEMPLATE, report=report)

@app.route("/api/report")
def api_report(): return jsonify(report)

# ------------------ Main Entry ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EnvSync Pro - Unified MVP")
    parser.add_argument("--build", action="store_true", help="Build Docker image after scan")
    parser.add_argument("--dashboard", action="store_true", help="Launch Flask dashboard after scan")
    args = parser.parse_args()

    print("🔍 Scanning environment...")
    report = scan_environment()
    report["conflicts"] = detect_conflicts(report)

    save_json(report)
    save_html(report)
    generate_dockerfile(report)

    if args.build:
        print("🐳 Building Docker image envsync_pro:latest ...")
        os.system("docker build -t envsync_pro:latest .")

    if args.dashboard:
        print("🚀 Starting EnvSync Pro Dashboard")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        print("✅ EnvSync Pro complete: Reports + Dockerfile ready!")
