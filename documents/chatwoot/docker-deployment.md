# Chatwoot Docker Deployment Guide

## Deployment Prerequisites

### Docker Requirements:
- Recommended Docker version: 20.10.10+
- Docker Compose version: v2.14.1+

## Deployment Steps

### 1. Install Docker
```bash
apt-get update
apt-get upgrade
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
apt install docker-compose-plugin
```

### 2. Download Configuration Files
```bash
wget -O .env https://raw.githubusercontent.com/chatwoot/chatwoot/develop/.env.example
wget -O docker-compose.yaml https://raw.githubusercontent.com/chatwoot/chatwoot/develop/docker-compose.production.yaml
```

### 3. Configure Environment Variables
- Edit `.env` and `docker-compose.yaml`
- Update Redis and PostgreSQL passwords
- Configure environment-specific settings

Required Environment Variables:
```env
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=postgres  # Service name from docker-compose
POSTGRES_PORT=5432
POSTGRES_DB=chatwoot
REDIS_URL=redis://redis:6379
SECRET_KEY_BASE=your_secret_key
```

### 4. Database Preparation
```bash
docker compose run --rm rails bundle exec rails db:chatwoot_prepare
```

This command will:
- Create the database if it doesn't exist
- Run all migrations
- Seed initial data

### 5. Start Services
```bash
docker compose up -d
```

## Database Troubleshooting

### Common Issues:

#### 1. "NoDatabaseError: We could not find your database"
**Cause:** Database hasn't been created or was deleted

**Solution:**
```bash
# Method 1: Run database preparation
docker compose run --rm rails bundle exec rails db:chatwoot_prepare

# Method 2: Manual database creation
docker exec -it chatwoot bundle exec rails db:create
docker exec -it chatwoot bundle exec rails db:migrate
```

#### 2. "could not translate host name to address: Name does not resolve"
**Cause:** Container can't find PostgreSQL service on the network

**Solution:**
1. Check if containers are on the same network:
```bash
docker network inspect <project>_default
```

2. Verify postgres container name in environment:
```env
# Should match service name in docker-compose.yml
POSTGRES_HOST=postgres  # or chatwoot-postgres
```

3. Restart with proper network configuration:
```bash
docker-compose down
docker-compose up -d
```

#### 3. Database Connection Issues
**Check container connectivity:**
```bash
# From chatwoot container, test postgres connection
docker exec -it chatwoot ping postgres

# Check if postgres is listening
docker exec -it postgres psql -U postgres -c "SELECT 1"
```

### Database Reset (CAUTION: Deletes all data)
```bash
docker compose down -v  # Remove volumes
docker compose up -d
docker compose run --rm rails bundle exec rails db:chatwoot_prepare
```

## Upgrading Chatwoot

```bash
docker compose pull
docker compose up -d
docker compose run --rm rails bundle exec rails db:chatwoot_prepare
```

## Additional Configuration

### Nginx Reverse Proxy Setup
1. Install Nginx
2. Configure Nginx to proxy requests to Chatwoot
3. Set up SSL with Let's Encrypt

### Access Rails Console
```bash
docker exec -it chatwoot sh -c 'RAILS_ENV=production bundle exec rails c'
```

### Verify Installation
```bash
curl -I localhost:3000/api
```

## Docker Image Variants
- Production: Use `latest` tag
- Community Edition: Use `latest-ce` or version-specific `-ce` tags

## Important Notes
- Containers bind to localhost by default
- Use a proxy server like Nginx for external access
- Run database preparation script during updates
- Keep environment variables secure
- Regular backups of PostgreSQL data recommended

## Source
Documentation from: https://developers.chatwoot.com/self-hosted/deployment/docker
