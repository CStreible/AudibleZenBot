# Start ngrok tunnels with specified flags
# Usage: .\start_ngrok.ps1 -Port 5000

param(
    [Parameter(Mandatory=$true)]
    [int]$Port
)

Write-Host "Starting ngrok tunnel on port $Port with pooling enabled..." -ForegroundColor Green

# Start ngrok with pooling-enabled flag
ngrok http $Port --pooling-enabled
