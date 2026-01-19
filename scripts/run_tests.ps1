# Run tests using the workspace venv when available
$python = "python"
if (Test-Path ".venv-1\Scripts\python.exe") { $python = ".venv-1\Scripts\python.exe" }
Write-Host "Using: $python"
& $python -m unittest discover -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }