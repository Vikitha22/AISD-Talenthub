#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
