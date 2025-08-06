# EnvSync Pro

EnvSync Pro is a one-click environment scanner, dependency conflict detector, 
and reproducibility tool with live auto-refreshing web dashboard.

## Features
- Scan Python, Node.js, Java environments
- Detect dependency conflicts (Python, Node, Java)
- Generate JSON + HTML report
- One-click Dockerfile for environment reproducibility
- Live Flask dashboard with `/api/report` endpoint
- Auto-refresh every 30s for live monitoring

## Local Run
```bash
python envsync_pro.py --dashboard
