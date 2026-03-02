#!/usr/bin/env bash
# arXiv Paper Briefing 웹 대시보드 실행 스크립트
set -e

PYTHON="/home/bskang/miniconda3/envs/Papers/bin/python"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"
exec "$PYTHON" app.py
