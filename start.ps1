#!/usr/bin/env pwsh
# Start the GitHub Onboarding Tool and open the browser

Write-Host "Starting GitHub Onboarding Tool..." -ForegroundColor Green

# Start Docker Compose
docker-compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Containers started successfully!" -ForegroundColor Green
    Write-Host "Waiting for application to be ready..." -ForegroundColor Yellow
    
    # Wait for the application to be healthy (max 60 seconds)
    $maxAttempts = 30
    $attempt = 0
    $url = "http://localhost/health"
    
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "Application is ready!" -ForegroundColor Green
                
                # Open browser
                Write-Host "Opening browser at http://localhost" -ForegroundColor Cyan
                Start-Process "http://localhost"
                
                Write-Host "`nApplication is running!" -ForegroundColor Green
                Write-Host "  - Frontend: http://localhost" -ForegroundColor White
                Write-Host "  - API Docs: http://localhost/docs" -ForegroundColor White
                Write-Host "  - Backend API: http://localhost/api/" -ForegroundColor White
                Write-Host "`nTo stop: docker-compose down" -ForegroundColor Yellow
                exit 0
            }
        } catch {
            # Ignore errors and retry
        }
        
        $attempt++
        Start-Sleep -Seconds 2
    }
    
    Write-Host "Warning: Application didn't respond in time, but containers are running." -ForegroundColor Yellow
    Write-Host "Check manually at: http://localhost" -ForegroundColor White
    Start-Process "http://localhost"
} else {
    Write-Host "Failed to start containers!" -ForegroundColor Red
    exit 1
}
