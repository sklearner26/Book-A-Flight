# Docker Setup Guide for Book-A-Flight

This guide explains how to build and run the Book-A-Flight application using Docker.

## Prerequisites

- Docker: [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- Docker Compose: [Install Docker Compose](https://docs.docker.com/compose/install/)
- GROQ API Key: Required for the LLM functionality

## Quick Start

### 1. Prepare Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Or create manually:

```
GROQ_API_KEY=your_groq_api_key_here
```

### 2. Build and Run with Docker Compose (Recommended)

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8000`

### 3. Build and Run with Docker CLI

**Build the image:**
```bash
docker build -t book-a-flight:latest .
```

**Run the container:**
```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_groq_api_key_here \
  -v $(pwd):/app \
  book-a-flight:latest
```

## Accessing the Application

- **Web Interface:** http://localhost:8000
- **Health Check:** http://localhost:8000/health
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **ReDoc:** http://localhost:8000/redoc

## Useful Docker Commands

### View logs
```bash
docker-compose logs -f book-a-flight
```

### Stop the application
```bash
docker-compose down
```

### Remove containers and images
```bash
docker-compose down -v
docker rmi book-a-flight:latest
```

### Enter container shell
```bash
docker-compose exec book-a-flight bash
```

### Rebuild image
```bash
docker-compose up --build --force-recreate
```

## Development Mode

The docker-compose.yml includes volume mounts for live code reloading:

```yaml
volumes:
  - .:/app  # This enables hot-reload
```

Any changes to your Python files will automatically reload the application (if running with `uvicorn` in reload mode).

## Production Deployment

For production, consider:

1. **Remove volume mounts** in docker-compose.yml
2. **Set `reload=False`** in uvicorn configuration
3. **Use environment-specific config** separate from development
4. **Scale with multiple replicas** if using orchestration (Kubernetes, Swarm)
5. **Use a reverse proxy** (Nginx) in front of the app
6. **Enable HTTPS/TLS** for secure communication

Example production docker-compose.yml:
```yaml
version: '3.8'
services:
  book-a-flight:
    build: .
    container_name: book-a-flight-prod
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    restart: always
    deploy:
      replicas: 3
```

## Troubleshooting

### Container exits immediately
- Check logs: `docker-compose logs book-a-flight`
- Verify GROQ_API_KEY is set in .env file

### Port already in use
```bash
# Change port mapping in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### Permission denied errors
- Ensure .env file has correct permissions
- On Linux: `chmod 600 .env`

### Memory issues
- Increase Docker memory allocation
- In Docker Desktop: Settings → Resources → Memory

## Performance Tips

1. **Use BuildKit for faster builds:**
   ```bash
   DOCKER_BUILDKIT=1 docker build -t book-a-flight:latest .
   ```

2. **Layer caching:** Keep requirements.txt separate to leverage Docker's layer caching

3. **Multi-stage builds:** Can be added to reduce final image size if needed

## Network Configuration

The application uses a custom Docker network (`book-a-flight-network`) for service communication. To add additional services (database, cache, etc.):

1. Add service to docker-compose.yml
2. Use service name as hostname (e.g., `postgres:5432`)
3. All services will automatically be on the same network

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
