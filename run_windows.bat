@echo off
echo PocketSmart AI - Windows launcher
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo Run: py -3.14 -m venv .venv
  echo Then: .venv\Scripts\activate.bat
  echo Then: python -m pip install -r requirements.txt
  pause
  exit /b 1
)
.venv\Scripts\python.exe app.py
