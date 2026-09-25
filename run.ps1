Write-Host "PocketSmart AI - Windows launcher"
if (!(Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Virtual environment not found."
  Write-Host "Run: py -3.14 -m venv .venv"
  Write-Host "Then: .\.venv\Scripts\Activate.ps1"
  Write-Host "Then: python -m pip install -r requirements.txt"
  exit 1
}
.\.venv\Scripts\python.exe app.py
