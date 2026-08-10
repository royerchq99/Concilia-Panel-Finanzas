#!/bin/bash
# Lanzador para Mac: doble clic sobre este archivo.
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 abrir.py
elif command -v python >/dev/null 2>&1; then
  python abrir.py
else
  echo ""
  echo "  No encuentro Python en este ordenador."
  echo "  Instalalo desde https://python.org/downloads"
  echo ""
  read -p "  Pulsa Intro para cerrar..."
fi
