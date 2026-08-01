$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    throw "Virtual environment belum tersedia. Jalankan .\scripts\setup.ps1"
}

& .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
