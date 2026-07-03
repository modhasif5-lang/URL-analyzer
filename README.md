# Smart URL Analyzer API

A **production-ready REST API** built with FastAPI that accepts a webpage URL, analyzes it asynchronously using Celery workers, caches results in Redis, and is fully containerized with Docker for deployment on AWS EC2.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (curl / browser)                  │
│                                                                 │
│   POST /analyze ──► GET /status/{id} ──► GET /result/{id}       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DOCKER COMPOSE NETWORK                      │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────┐  │
│  │   FastAPI (API)   │───▶│  Redis (Cache +  │◀───│  Celery   │  │
│  │   :8000           │    │  Broker + Backend)│    │  Worker   │  │
│  │                   │    │  :6379            │    │           │  │
│  │  • /analyze       │    │                   │    │  • Tasks  │  │
│  │  • /status/{id}   │    │  • Cache (DB 0)   │    │  • Retry  │  │
│  │  • /result/{id}   │    │  • Broker (DB 1)  │    │  • Scrape │  │
│  │  • /health        │    │  • Backend (DB 2) │    │  • Parse  │  │
│  └──────────────────┘    └──────────────────┘    └───────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Flow:**
1. Client sends a URL via `POST /analyze`
2. API checks Redis cache → returns cached result if available
3. Otherwise, submits an async Celery task → returns `task_id`
4. Celery worker downloads, parses, and analyzes the page
5. Result is cached in Redis with a 1-hour TTL
6. Client polls `GET /status/{task_id}` then retrieves `GET /result/{task_id}`

---

## Folder Structure

```
url-analyzer/
├── app/
│   ├── __init__.py          # Package init
│   ├── main.py              # FastAPI application & endpoints
│   ├── config.py            # Settings from environment variables
│   ├── celery_app.py        # Celery application factory
│   ├── cache.py             # Redis cache operations
│   ├── scraper.py           # Webpage download & analysis
│   ├── tasks.py             # Celery task definitions
│   ├── schemas.py           # Pydantic request/response models
│   ├── utils.py             # Utility functions
│   └── logging_config.py    # Rotating log configuration
├── tests/
│   ├── test_api.py          # API endpoint tests
│   ├── test_cache.py        # Cache layer tests
│   ├── test_scraper.py      # Scraper function tests
│   └── test_tasks.py        # Celery task tests
├── logs/                    # Log file output directory
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Multi-service orchestration
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── README.md                # This file
└── run_local.sh             # Local development helper script
```

---

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- OR: Python 3.12 + Redis (for local development)

### Run with Docker (recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/url-analyzer.git
cd url-analyzer

# Build and start all services
docker compose up --build
```

The API will be available at **http://localhost:8000**.

### Run Locally (without Docker)

```bash
# Ensure Redis is running on localhost:6379
chmod +x run_local.sh
./run_local.sh
```

---

## API Documentation

### Swagger UI

Once running, visit: **http://localhost:8000/docs**

### ReDoc

Alternative docs: **http://localhost:8000/redoc**

---

## API Endpoints

### `POST /analyze` — Submit URL for Analysis

**Request:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Response (new task):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "cache_hit": false,
  "result": null,
  "message": "Task submitted for processing."
}
```

**Response (cached):**
```json
{
  "task_id": null,
  "cache_hit": true,
  "result": {
    "url": "https://example.com",
    "title": "Example Domain",
    "response_time_seconds": 0.4321,
    "word_count": 58,
    "top_keywords": [
      {"word": "domain", "count": 3},
      {"word": "example", "count": 2}
    ],
    "cache_hit": true,
    "analyzed_at": "2026-01-01T00:00:00+00:00"
  },
  "message": "Result retrieved from cache."
}
```

---

### `GET /status/{task_id}` — Check Task Status

```bash
curl http://localhost:8000/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS"
}
```

Possible statuses: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`

---

### `GET /result/{task_id}` — Get Analysis Result

```bash
curl http://localhost:8000/result/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response (success):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS",
  "result": {
    "url": "https://example.com",
    "title": "Example Domain",
    "response_time_seconds": 0.4321,
    "word_count": 58,
    "top_keywords": [
      {"word": "domain", "count": 3},
      {"word": "example", "count": 2}
    ],
    "cache_hit": false,
    "analyzed_at": "2026-01-01T00:00:00+00:00"
  },
  "error": null
}
```

---

### `GET /health` — Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "api": {"status": "healthy", "detail": "API is running."},
  "redis": {"status": "healthy", "detail": "Redis is reachable."},
  "celery": {"status": "healthy", "detail": "1 worker(s) active."}
}
```

---

## Testing

### Run all tests

```bash
# With Docker
docker compose exec api pytest tests/ -v

# Locally (with venv activated)
pytest tests/ -v
```

### Run specific test files

```bash
pytest tests/test_api.py -v
pytest tests/test_scraper.py -v
pytest tests/test_cache.py -v
pytest tests/test_tasks.py -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL for caching |
| `CACHE_TTL` | `3600` | Cache expiry in seconds |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery message broker URL |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery result storage URL |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `logs/app.log` | Log file path |
| `REQUEST_TIMEOUT` | `15` | HTTP request timeout in seconds |
| `MAX_RETRIES` | `3` | Max Celery task retries |
| `API_TITLE` | `Smart URL Analyzer API` | API title in docs |
| `API_VERSION` | `1.0.0` | API version string |

---

## AWS EC2 Deployment Guide

### 1. Launch an EC2 Instance

- **AMI:** Ubuntu 22.04 LTS
- **Instance type:** t3.small (minimum) or t3.medium (recommended)
- **Storage:** 20 GB gp3

### 2. Configure Security Groups

Open the following inbound ports:

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | Your IP | SSH access |
| 8000 | TCP | 0.0.0.0/0 | API access |

### 3. Connect and Install Docker

```bash
# SSH into your instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose-v2
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (avoids sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### 4. Deploy the Application

```bash
# Clone the repository
git clone https://github.com/your-username/url-analyzer.git
cd url-analyzer

# Build and start in detached mode
docker compose up --build -d
```

### 5. Verify Deployment

```bash
# Check running containers
docker compose ps

# Test health endpoint
curl http://localhost:8000/health

# View logs
docker compose logs -f
```

### 6. Managing the Application

```bash
# Stop all services
docker compose down

# Restart services
docker compose restart

# Update application
git pull origin main
docker compose up --build -d

# View API logs only
docker compose logs -f api

# View worker logs only
docker compose logs -f worker

# Scale workers
docker compose up -d --scale worker=3
```

### 7. Production Hardening (Optional)

- **Reverse proxy:** Place Nginx or Caddy in front for SSL termination
- **Domain:** Point a domain to your EC2 elastic IP
- **Monitoring:** Use CloudWatch or Prometheus + Grafana
- **Backups:** Snapshot EBS volumes regularly
- **Secrets:** Use AWS Secrets Manager instead of `.env` files

---

## 🔮 Future Improvements

- [ ] **Database** — PostgreSQL for persistent analysis history
- [ ] **Flower** — Celery monitoring dashboard
- [ ] **CI/CD** — GitHub Actions pipeline for automated testing and deployment

---

## Troubleshooting

### Container won't start

```bash
docker compose logs api
docker compose logs worker
```

### Redis connection refused

Check Redis is running:
```bash
docker compose ps redis
docker compose exec redis redis-cli ping
```

### Celery worker not processing tasks

```bash
# Check worker status
docker compose logs worker

# Verify broker connectivity
docker compose exec worker celery -A app.celery_app:celery_app inspect ping
```

### Port 8000 already in use

```bash
# Find the process using port 8000
lsof -i :8000
# Kill it or change the port in docker-compose.yml
```

### Tests failing

```bash
# Ensure you're running tests with mocks (no Redis/Celery needed)
pytest tests/ -v --tb=short
```

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
