#!/usr/bin/env bash

set -e

echo "======================================"
echo " Oil & Gas Data Engineering Pipeline"
echo "======================================"

PYTHONPATH=. ./.venv/Scripts/python.exe -m src.main

echo
echo "Pipeline finished successfully."