$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host ""
Write-Host "Setup selesai."
Write-Host "Salin .env.example menjadi .env, lalu sesuaikan koneksi MySQL Laragon."
