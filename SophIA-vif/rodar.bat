@echo off
REM Sobe a SophIA. Na primeira vez, monta o ambiente sozinho.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo ===================================================================
  echo  Primeira execucao: preparando o ambiente. Leva 1 ou 2 minutos.
  echo  Isso acontece so uma vez.
  echo ===================================================================
  echo.
  python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Nao encontrei o Python. Instale em python.org, marcando a opcao
    echo  "Add Python to PATH" durante a instalacao, e rode este arquivo
    echo  de novo.
    echo.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo  Falhou a instalacao das bibliotecas. Confira sua internet e
    echo  rode este arquivo de novo.
    echo.
    pause
    exit /b 1
  )
  echo.
  echo  Ambiente pronto.
  echo.
)

".venv\Scripts\python.exe" "run.py" %*
pause
