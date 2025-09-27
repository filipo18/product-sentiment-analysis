# PowerShell script to replace Makefile functionality
param(
    [Parameter(Position=0)]
    [string]$Command
)

# Set environment variables
$env:PYTHONPATH = $PWD

# Function to run commands
function Invoke-Command {
    param([string]$cmd)
    Write-Host "Running: $cmd" -ForegroundColor Green
    Invoke-Expression $cmd
}

# Main command logic
switch ($Command) {
    "install" {
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        Invoke-Command "pip install -r requirements.txt"
    }
    "dev" {
        Write-Host "Starting development server..." -ForegroundColor Yellow
        Invoke-Command "uvicorn app.main:app --reload --port 8000"
    }
    "ingest" {
        Write-Host "Running data ingestion..." -ForegroundColor Yellow
        Invoke-Command "python scripts/run_ingest.py"
    }
    "classify" {
        Write-Host "Running classification..." -ForegroundColor Yellow
        Invoke-Command "python scripts/run_classify.py"
    }
    "dashboard" {
        Write-Host "Starting Streamlit dashboard..." -ForegroundColor Yellow
        Invoke-Command "streamlit run streamlit_app/app.py"
    }
    "lint" {
        Write-Host "Running type checking..." -ForegroundColor Yellow
        Invoke-Command "mypy app"
    }
    "test" {
        Write-Host "Running tests..." -ForegroundColor Yellow
        Invoke-Command "pytest"
    }
    default {
        Write-Host "Available commands:" -ForegroundColor Cyan
        Write-Host "  install    - Install dependencies" -ForegroundColor White
        Write-Host "  dev        - Start development server" -ForegroundColor White
        Write-Host "  ingest     - Run data ingestion" -ForegroundColor White
        Write-Host "  classify   - Run classification" -ForegroundColor White
        Write-Host "  dashboard  - Start Streamlit dashboard" -ForegroundColor White
        Write-Host "  lint       - Run type checking" -ForegroundColor White
        Write-Host "  test       - Run tests" -ForegroundColor White
        Write-Host ""
        Write-Host "Usage: .\run.ps1 <command>" -ForegroundColor Yellow
        Write-Host "Example: .\run.ps1 dev" -ForegroundColor Yellow
    }
}