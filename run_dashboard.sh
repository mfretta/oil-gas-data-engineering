#!/usr/bin/env bash

set -e

echo "======================================"
echo " Oil & Gas Intelligence Dashboard"
echo "======================================"

PYTHONPATH=. ./.venv/Scripts/python.exe -m streamlit run src/dashboard/app.py