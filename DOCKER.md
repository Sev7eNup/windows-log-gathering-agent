# Docker Deployment Guide

This guide covers deploying the Windows Log Gathering Agent using Docker containers.

## 🏗️ Architecture

The application consists of multiple containerized services:

- **Backend** (FastAPI API server)
- **Frontend** (React + Nginx)
- **Redis** (Caching and session storage)
- **PowerShell MCP Server** (PowerShell operations)
- **SMB MCP Server** (SMB file access)

## 🚀 Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- At least 4GB RAM available for containers

### 2. Configuration

Copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```bash
# Essential configurations
LGA_CONFIG_FILE=config/machines.yaml
DOMAIN_USERNAME=DOMAIN\\admin
DOMAIN_PASSWORD=your_password
LLM_ENDPOINT=http://localhost:11434/v1
```

### 3. Start Services

#### Production deployment:
```bash
docker-compose up -d
```

#### Development with hot reload:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 4. Access the Application

- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📋 Available Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React web interface |
| Backend | 8000 | FastAPI REST API |
| Redis | 6379 | Cache and sessions |
| PowerShell MCP | 8001 | PowerShell operations |
| SMB MCP | 8002 | SMB file access |
| Nginx Proxy | 80, 443 | Reverse proxy |

## 🔧 Management Commands

### View running containers:
```bash
docker-compose ps
```

### View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Stop services:
```bash
docker-compose down
```

### Rebuild containers:
```bash
docker-compose build
docker-compose up -d --force-recreate
```

### Update containers:
```bash
docker-compose pull
docker-compose up -d
```

## 🐛 Troubleshooting

### Container won't start:
```bash
# Check container status
docker-compose ps

# Check logs for errors
docker-compose logs backend

# Restart specific service
docker-compose restart backend
```

### Reset everything:
```bash
# Stop and remove all containers/volumes
docker-compose down -v

# Remove images (optional)
docker-compose down --rmi all

# Start fresh
docker-compose up -d
```

### Performance issues:
```bash
# Monitor resource usage
docker stats

# Check container health
docker-compose ps
```

## 📊 Health Checks

All services include health checks:

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend health
curl http://localhost:3000/

# Check Redis
docker-compose exec redis redis-cli ping
```

## 🔐 Security Considerations

### Production deployment:

1. **Use HTTPS**: Configure SSL certificates in nginx
2. **Secure credentials**: Use Docker secrets or external credential stores
3. **Network isolation**: Use custom Docker networks
4. **Resource limits**: Set memory and CPU limits
5. **Regular updates**: Keep base images updated

### Example production override:
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
    restart: always
    
  frontend:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'
    restart: always
```

## 📦 Data Persistence

Persistent volumes are configured for:

- **Application data**: `agent_data` volume
- **Redis data**: `redis_data` volume
- **Configuration**: Bind-mounted from `./config`
- **Logs**: Bind-mounted from `./logs`

### Backup data:
```bash
# Create backup
docker run --rm -v log-agent-data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data

# Restore backup  
docker run --rm -v log-agent-data:/data -v $(pwd):/backup alpine tar xzf /backup/data-backup.tar.gz -C /
```

## 🎯 Development

### Development setup with hot reload:
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View development logs
docker-compose -f docker-compose.dev.yml logs -f

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Building custom images:
```bash
# Build specific service
docker-compose build backend

# Build all services
docker-compose build

# Build with no cache
docker-compose build --no-cache
```

## 🚀 Production Deployment

### 1. Environment setup:
```bash
# Create production environment
cp .env.example .env.prod

# Edit production settings
vi .env.prod
```

### 2. SSL Configuration:
```bash
# Create SSL directory
mkdir -p docker/nginx/ssl

# Copy SSL certificates
cp your-cert.crt docker/nginx/ssl/
cp your-key.key docker/nginx/ssl/
```

### 3. Deploy:
```bash
# Deploy to production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📝 Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `LGA_CONFIG_FILE`: Path to machine configuration
- `LGA_DEBUG`: Enable debug mode
- `DOMAIN_USERNAME/PASSWORD`: Windows domain credentials
- `LLM_ENDPOINT`: Local LLM endpoint URL

## 🆘 Support

For issues:
1. Check container logs: `docker-compose logs`
2. Verify configuration: `docker-compose config`
3. Check resource usage: `docker stats`
4. Review health checks: Service-specific health endpoints