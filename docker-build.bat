@echo off
:: Build and deployment script for Clause Explainer Docker setup (Windows version)

setlocal enabledelayedexpansion

:: Check if .env exists
:check_env
if not exist .env (
    echo [WARNING] .env file not found. Copying from .env.example...
    copy .env.example .env
    echo [WARNING] Please edit .env file with your API keys before proceeding.
    pause
    exit /b 1
)
goto :eof

:: Build Docker image
:build
echo [INFO] Building Docker image...
docker build -t clause-explainer:latest .
if %errorlevel% neq 0 (
    echo [ERROR] Docker build failed
    exit /b 1
)
echo [SUCCESS] Docker image built successfully
goto :eof

:: Start services
:start
echo [INFO] Starting services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services
    exit /b 1
)

echo [INFO] Waiting for services to be ready...
timeout /t 30 /nobreak >nul

:: Check health
curl -f http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Services are running and healthy!
    echo [INFO] API Documentation: http://localhost:8000/docs
    echo [INFO] Health Check: http://localhost:8000/health
) else (
    echo [ERROR] Services failed to start properly
    echo [INFO] Check logs with: docker-compose logs
    exit /b 1
)
goto :eof

:: Start development environment
:dev
echo [INFO] Starting development environment...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
echo [INFO] Development environment started with live reload
docker-compose logs -f clause-explainer
goto :eof

:: Stop services
:stop
echo [INFO] Stopping services...
docker-compose down
echo [SUCCESS] Services stopped
goto :eof

:: Clean up everything
:clean
echo [WARNING] This will remove all containers, images, and volumes
set /p confirm="Are you sure? (y/N): "
if /i "!confirm!"=="y" (
    docker-compose down -v
    docker rmi clause-explainer:latest 2>nul
    echo [SUCCESS] Cleanup completed
) else (
    echo [INFO] Cleanup cancelled
)
goto :eof

:: Show logs
:logs
docker-compose logs -f %2 %3 %4 %5
goto :eof

:: Show status
:status
echo [INFO] Service Status:
docker-compose ps

echo.
echo Health Checks:
curl -s http://localhost:8000/health >nul 2>&1 && (
    echo Main API: ✅ Healthy
) || (
    echo Main API: ❌ Unhealthy
)

docker-compose exec -T mongodb mongosh --eval "db.runCommand({ping:1})" >nul 2>&1 && (
    echo MongoDB: ✅ Healthy
) || (
    echo MongoDB: ❌ Unhealthy
)

curl -s http://localhost:6333/health >nul 2>&1 && (
    echo Qdrant: ✅ Healthy
) || (
    echo Qdrant: ❌ Unhealthy
)
goto :eof

:: Help
:help
echo Clause Explainer Docker Management Script
echo.
echo Usage: %0 [COMMAND]
echo.
echo Commands:
echo   build     Build Docker image
echo   start     Start all services
echo   dev       Start development environment with live reload
echo   stop      Stop all services
echo   clean     Remove all containers, images, and volumes
echo   logs      Show logs (optionally specify service name)
echo   status    Show service status and health
echo   help      Show this help message
echo.
echo Examples:
echo   %0 start                    # Start production environment
echo   %0 dev                      # Start development environment
echo   %0 logs clause-explainer    # Show logs for main service
echo   %0 status                   # Check service health
goto :eof

:: Main script
if "%1"=="" goto help
if "%1"=="build" (
    call :check_env && call :build
) else if "%1"=="start" (
    call :check_env && call :start
) else if "%1"=="dev" (
    call :check_env && call :dev
) else if "%1"=="stop" (
    call :stop
) else if "%1"=="clean" (
    call :clean
) else if "%1"=="logs" (
    call :logs %*
) else if "%1"=="status" (
    call :status
) else (
    call :help
)