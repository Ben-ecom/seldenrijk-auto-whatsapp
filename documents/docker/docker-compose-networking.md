# Docker Compose Networking Guide

## Key Networking Concepts

### 1. Default Network Behavior
- Compose automatically creates a single network for your application
- Each service container joins this default network
- Containers can discover and communicate with each other using service names
- Network name is based on the project directory name

### 2. Service-to-Service Communication
- Services can connect using their service name as the hostname
- Example connection string: `postgres://db:5432`
- Containers use container ports for internal communication
- Host ports enable external access

### 3. Network Configuration Options

#### Custom Networks:
- Define custom networks using top-level `networks` key
- Specify network drivers and options
- Control service isolation by defining network connections
- Configure static IP addresses
- Create named networks

#### Network Types:
- Default app-wide network
- Custom bridge networks
- Overlay networks for multi-host communication
- External pre-existing networks

### 4. Advanced Networking Features
- Link containers with additional hostname aliases
- Configure default network settings
- Use existing networks with `external: true`
- Support for multi-host networking in Swarm mode

## Best Practices
- Reference containers by name, not IP address
- Use container ports for inter-service communication
- Leverage Compose's built-in service discovery
- Define clear network topologies for complex applications

## Example Configuration

```yaml
services:
  web:
    build: .
    networks:
      - frontend
  db:
    image: postgres
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: custom-driver
```

## Troubleshooting Container Connectivity

### Common Issues:

1. **Container name resolution fails**
   - Check if containers are on the same network
   - Use `docker network inspect <network_name>` to verify
   - Ensure service names match docker-compose.yml

2. **"Name does not resolve" error**
   - Container might be on different network
   - Network may not exist
   - Check with: `docker network ls`

3. **Connection refused**
   - Check if target service is running
   - Verify port bindings
   - Check firewall rules

### Debugging Commands:

```bash
# List all networks
docker network ls

# Inspect a specific network
docker network inspect <network_name>

# Check container network settings
docker inspect <container_name> | grep -A 20 Networks

# Test connectivity between containers
docker exec <container_name> ping <target_service_name>
```

## Source
Documentation from: https://docs.docker.com/compose/networking/
