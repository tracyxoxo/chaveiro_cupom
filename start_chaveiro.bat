@echo off
title Chaveiro Brotero - Cupom

REM Vai para a pasta do projeto
cd /d %~dp0

REM Ativa o ambiente virtual
CALL venv\Scripts\activate.bat

REM Abre o navegador
start "" http://127.0.0.1:8000

REM Executa uvicorn pelo Python da venv
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
