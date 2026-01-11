# Brand Analytics Deployment Guide

## Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

## Quick Start

```bash
# Clone and setup
git clone https://github.com/xkonjin/brand-analytics
cd brand-analytics

# Copy environment files
cp .env.example .env
# Edit .env with your values

# Start with Docker
docker-compose up -d
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `REDIS_URL` | Redis for caching | No |

## Production Deployment

### Vercel (Frontend)
```bash
vercel --prod
```

### Railway/Render (Backend)
Use the included Dockerfile.

## Monitoring
- Health check: `/api/health`
- Metrics: `/api/metrics`
