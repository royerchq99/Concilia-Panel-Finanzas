@echo off
chcp 65001 >nul
title Panel de conciliacion de pautas
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python abrir.py
    goto :fin
)

where py >nul 2>nul
if %errorlevel%==0 (
    py abrir.py
    goto :fin
)

echo.
echo   No encuentro Python en este ordenador.
echo.
echo   Instalalo desde https://python.org/downloads
echo   IMPORTANTE: marca la casilla "Add Python to PATH" al instalar.
echo.
pause

:fin
