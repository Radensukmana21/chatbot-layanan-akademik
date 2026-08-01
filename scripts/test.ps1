$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    throw "Virtual environment belum tersedia. Jalankan .\scripts\setup.ps1"
}

& .\.venv\Scripts\Activate.ps1
pytest
