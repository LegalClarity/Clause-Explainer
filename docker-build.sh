#!/bin/bash

# Build and deployment script for Clause Explainer Docker setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        log_warning ".env file not found. Copying from .env.example..."
        cp .env.example .env
        log_warning "Please edit .env file with your API keys before proceeding."
        return 1
    fi
    return 0
}

# Build Docker image
build() {
    log_info "Building Docker image..."
    docker build -t clause-explainer:latest .
    log_success "Docker image built successfully"
}

# Start services
start() {
    log_info "Starting services..."
    docker-compose up -d
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Services are running and healthy!"
        log_info "API Documentation: http://localhost:8000/docs"
        log_info "Health Check: http://localhost:8000/health"
    else
        log_error "Services failed to start properly"
        log_info "Check logs with: docker-compose logs"
        return 1
    fi
}

# Start development environment
dev() {
    log_info "Starting development environment..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    log_info "Development environment started with live reload"
    docker-compose logs -f clause-explainer
}

# Stop services
stop() {
    log_info "Stopping services..."
    docker-compose down
    log_success "Services stopped"
}

# Clean up everything
clean() {
    log_warning "This will remove all containers, images, and volumes"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        docker rmi clause-explainer:latest 2>/dev/null || true
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

# Show logs
logs() {
    docker-compose logs -f "$@"
}

# Show status
status() {
    log_info "Service Status:"
    docker-compose ps
    
    echo -e "\n${BLUE}Health Checks:${NC}"
    echo "Main API: $(curl -s http://localhost:8000/health > /dev/null && echo "✅ Healthy" || echo "❌ Unhealthy")"
    echo "MongoDB: $(docker-compose exec -T mongodb mongosh --eval 'db.runCommand({ping:1})' > /dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy")"
    echo "Qdrant: $(curl -s http://localhost:6333/health > /dev/null && echo "✅ Healthy" || echo "❌ Unhealthy")"
}

# Help
help() {
    echo "Clause Explainer Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build     Build Docker image"
    echo "  start     Start all services"
    echo "  dev       Start development environment with live reload"
    echo "  stop      Stop all services"
    echo "  clean     Remove all containers, images, and volumes"
    echo "  logs      Show logs (optionally specify service name)"
    echo "  status    Show service status and health"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start production environment"
    echo "  $0 dev                      # Start development environment"
    echo "  $0 logs clause-explainer    # Show logs for main service"
    echo "  $0 status                   # Check service health"
}

# Main script
case "${1:-help}" in
    build)
        check_env && build
        ;;
    start)
        check_env && start
        ;;
    dev)
        check_env && dev
        ;;
    stop)
        stop
        ;;
    clean)
        clean
        ;;
    logs)
        shift
        logs "$@"
        ;;
    status)
        status
        ;;
    help|*)
        help
        ;;
esac