#!/bin/bash

# install_linux.sh — Setup script for Linux/macOS

set -e

echo ">>> Creating virtual environment in '.venv' if not exists..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo ">>> Activating virtual environment..."
source .venv/bin/activate

echo ">>> Upgrading pip..."
pip install --upgrade pip

echo ">>> Installing project requirements..."
pip install -r requirements.txt

echo ">>> Setup completed successfully!"
echo ""
echo "To activate your environment later:"
echo "  source .venv/bin/activate"
