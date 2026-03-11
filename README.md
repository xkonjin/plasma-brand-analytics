# 🚀 Brand Analytics

> **AI-Powered 360° Brand Audit Platform for Startups**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)

---

## 📖 Overview

**Brand Analytics** is an automated virtual brand analyst that delivers consulting-grade marketing audits in minutes instead of weeks. In a world where traditional agency audits cost thousands and take weeks to complete, this platform provides instant, actionable insights across 8 critical brand dimensions.

### The Problem We Solve

- ❌ Traditional brand audits: **$5,000-$15,000** and **2-4 weeks**
- ✅ Brand Analytics: **$0.10** and **2 minutes**

### 8-Dimensional Analysis

| Module | Weight | What It Analyzes |
|--------|--------|-----------------|
| 🔍 **SEO Performance** | 15% | Core Web Vitals, meta tags, indexing, domain authority |
| 🤖 **AI Discoverability** | 10% | Wikipedia presence, Knowledge Graph, LLM visibility |
| 📱 **Social Media** | 20% | Followers, engagement rates, posting consistency |
| 🎭 **Brand Messaging** | 15% | Archetype identification, tone analysis, value proposition |
| 🎨 **Website UX** | 15% | CTAs, navigation, trust signals, conversion readiness |
| 📝 **Content Analysis** | 10% | Content mix, sentiment analysis, topic coverage |
| 👥 **Team Presence** | 10% | Team visibility, founder credibility, LinkedIn signals |
| 📊 **Channel Fit** | 5% | Marketing channel recommendations and prioritization |

---

## ✨ Key Features

- ⚡ **Lightning Fast** - Complete analysis in under 2 minutes
- 🎯 **Comprehensive Scoring** - 0-100 weighted brand health score with letter grades (A+ to F)
- 📄 **PDF Reports** - Professional, downloadable audit reports
- 💳 **Web3 Payments** - x402 payment protocol integration (Plasma Network)
- 🔒 **No Signup Required** - Pay-per-analysis with crypto wallet
- 📊 **Real-time Progress** - Live updates as each module completes
- 🎨 **Beautiful UI** - Glass morphism design with fluid animations
- 🐳 **Docker Ready** - One-command local deployment
- 📈 **Benchmarking** - Compare against industry standards
- 🤖 **AI-Powered** - GPT-4o integration for brand archetype analysis

---

## 🏗 Architecture

### System Overview

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        Wallet["Web3 Wallet<br/>RainbowKit"]
    end

    subgraph Frontend["Frontend (Next.js 14)"]
        NextUI["React + TypeScript"]
        Tailwind["Tailwind CSS"]
        Framer["Framer Motion"]
        Wagmi["Wagmi / Viem"]
    end

    subgraph Backend["Backend (FastAPI)"]
        API["REST API Layer"]
        Auth["Authentication<br/>JWT + API Keys"]
        Orchestrator["Analysis Orchestrator"]
        
        subgraph Analyzers["8 Analysis Modules"]
            SEO["SEO Analyzer"]
            Social["Social Media"]
            Brand["Brand Messaging"]
            UX["Website UX"]
            AI["AI Discoverability"]
            Content["Content"]
            Team["Team Presence"]
            Channel["Channel Fit"]
        end
    end

    subgraph Workers["Background Workers"]
        Celery["Celery Workers"]
        Flower["Flower Monitoring"]
    end

    subgraph Data["Data Layer"]
        Postgres[(PostgreSQL)]
        Redis[(Redis<br/>Cache + Queue)]
    end

    subgraph External["External APIs"]
        OpenAI["OpenAI GPT-4o"]
        Google["Google PageSpeed"]
        Twitter["Twitter/X API"]
        Moz["Moz Links API"]
        Apify["Apify Scrapers"]
        Firecrawl["Firecrawl"]
        Perplexity["Perplexity AI"]
    end

    Browser --> NextUI
    Wallet --> Wagmi
    NextUI --> API
    API --> Auth
    API --> Orchestrator
    Orchestrator --> Analyzers
    Orchestrator --> Celery
    Celery --> Redis
    API --> Postgres
    Analyzers --> OpenAI
    Analyzers --> Google
    Analyzers --> Twitter
    Analyzers --> Moz
    Analyzers --> Apify
    Analyzers --> Firecrawl
    Analyzers --> Perplexity
```

### Analysis Pipeline

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Orchestrator
    participant Celery
    participant External

    User->>Frontend: Enter URL & Pay ($0.10)
    Frontend->>API: POST /api/v1/analyze
    API->>Orchestrator: Start Analysis
    Orchestrator->>Celery: Queue Background Task
    Celery-->>Frontend: WebSocket Progress Updates
    
    par Wave 1: External APIs
        Celery->>External: Google PageSpeed
        Celery->>External: Moz Domain Authority
        Celery->>External: Twitter Metrics
        Celery->>External: Wikipedia Check
    and Wave 2: AI Analysis
        Celery->>External: GPT-4o Brand Archetype
        Celery->>External: Content Analysis
    and Wave 3: Derived Analysis
        Celery->>Celery: Team Presence
        Celery->>Celery: Channel Fit
    end
    
    Celery->>Orchestrator: All Results
    Orchestrator->>Orchestrator: Generate Scorecard
    Orchestrator->>API: Complete Report
    API->>Frontend: Report Ready
    Frontend->>User: Display Results + PDF
```

### Directory Structure

```
brand-analytics/
├── 📁 backend/                    # Python FastAPI Application
│   ├── 📁 app/
│   │   ├── 📁 analyzers/          # 8 brand analysis modules
│   │   ├── 📁 api/                # REST API routes
│   │   ├── 📁 auth/               # JWT & API key authentication
│   │   ├── 📁 models/             # Pydantic & SQLAlchemy models
│   │   ├── 📁 scrapers/           # Website scraping logic
│   │   ├── 📁 services/           # External API integrations
│   │   ├── 📁 tasks/              # Celery background tasks
│   │   ├── 📁 middleware/         # Security & logging middleware
│   │   └── 📁 utils/              # Utilities (cache, scoring, etc.)
│   ├── 📁 tests/                  # pytest suite (72+ tests)
│   ├── 📁 alembic/                # Database migrations
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                 # Container definition
│   └── env.example                # Environment template
│
├── 📁 frontend/                   # Next.js 14 Application
│   ├── 📁 src/
│   │   ├── 📁 app/                # Next.js App Router pages
│   │   ├── 📁 components/         # React components
│   │   │   ├── 📁 report/         # Report visualization
│   │   │   ├── 📁 glass/          # Glass morphism UI
│   │   │   └── 📁 ui/             # shadcn/ui components
│   │   └── 📁 lib/                # Utilities, hooks, types
│   ├── package.json               # Node.js dependencies
│   ├── tailwind.config.js         # Tailwind configuration
│   ├── Dockerfile                 # Container definition
│   └── .env.local.example         # Environment template
│
├── docker-compose.yml             # Full stack orchestration
├── start-dev.sh                   # Development helper script
├── .env.example                   # Root env template
└── README.md                      # This file
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [Node.js 20+](https://nodejs.org/) (for local development)
- [Python 3.11+](https://www.python.org/) (for local development)
- API Keys (minimum: OpenAI)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/xkonjin/brand-analytics.git
cd brand-analytics

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (required)

# 3. Start all services
./start-dev.sh docker
# Or: docker-compose up -d

# 4. Access the application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Flower (Celery): http://localhost:5555
```

### Option 2: Local Development

```bash
# 1. Start infrastructure services
docker-compose up -d postgres redis

# 2. Terminal 1 - Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload --port 8000

# 3. Terminal 2 - Frontend
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local if needed
npm run dev
```

---

## ⚙️ Configuration

### Required Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPENAI_API_KEY` | GPT-4o for brand archetype analysis | ✅ Yes |

### Recommended Environment Variables

| Variable | Purpose | Get It At |
|----------|---------|-----------|
| `GOOGLE_API_KEY` | PageSpeed & Search API | [Google Cloud Console](https://console.cloud.google.com/) |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search Engine | [Programmable Search](https://programmablesearchengine.google.com/) |
| `TWITTER_BEARER_TOKEN` | Social media metrics | [Twitter Developer](https://developer.twitter.com/) |
| `MOZ_API_KEY` | Domain Authority, backlinks | [Moz API](https://moz.com/products/api) |
| `APIFY_API_TOKEN` | Instagram/YouTube/Reddit scraping | [Apify Console](https://console.apify.com/) |
| `FIRECRAWL_API_KEY` | JS-capable website scraping | [Firecrawl](https://www.firecrawl.dev/) |
| `PERPLEXITY_API_KEY` | Pre-analysis research | [Perplexity](https://www.perplexity.ai/settings/api) |

### Backend Environment (backend/.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/brand_analytics

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
TWITTER_BEARER_TOKEN=...

# Payment (x402 Protocol)
REQUIRE_PAYMENT=true
MERCHANT_ADDRESS=0x...
```

### Frontend Environment (frontend/.env.local)

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Web3 (RainbowKit)
NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID=...
```

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyze` | Start a new brand analysis |
| `GET` | `/api/v1/analysis/{id}` | Get analysis status & results |
| `GET` | `/api/v1/analysis/{id}/progress` | Get real-time progress |
| `GET` | `/api/v1/analysis/{id}/report` | Get complete report JSON |
| `GET` | `/api/v1/analysis/{id}/pdf` | Download PDF report |
| `POST` | `/api/v1/payments/invoice` | Create payment invoice (x402) |
| `GET` | `/api/v1/health` | Health check |

### Example: Start Analysis

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "description": "A DeFi lending platform",
    "industry": "crypto",
    "email": "founder@example.com"
  }'
```

### Example Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com",
  "status": "processing",
  "progress": {
    "seo": "completed",
    "social_media": "running",
    "brand_messaging": "pending"
  },
  "overall_score": null,
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Analysis in progress..."
}
```

---

## 📊 Scoring Methodology

### Weighted Score Calculation

| Module | Weight | Industry Benchmark |
|--------|--------|-------------------|
| Social Media | 20% | 55/100 |
| SEO Performance | 15% | 65/100 |
| Brand Messaging | 15% | 60/100 |
| Website UX | 15% | 70/100 |
| AI Discoverability | 10% | 40/100 |
| Content | 10% | 60/100 |
| Team Presence | 10% | 50/100 |
| Channel Fit | 5% | 55/100 |

### Grade Scale

| Score | Grade | Interpretation |
|-------|-------|----------------|
| 90-100 | A+ | Industry leader - Exceptional brand presence |
| 80-89 | A | Excellent - Strong foundation across all dimensions |
| 70-79 | B | Good - Above average with clear growth opportunities |
| 60-69 | C | Average - Room for improvement in key areas |
| 50-59 | D | Below average - Needs attention on fundamentals |
| 0-49 | F | Critical - Immediate action required |

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test suites
pytest tests/test_scoring.py -v        # 42 scoring tests
pytest tests/test_report_shape.py -v   # 30 report validation tests
```

### Frontend Tests

```bash
cd frontend

# Run E2E tests
npx playwright test

# Run with UI
npx playwright test --ui
```

---

## 🛠 Development Commands

```bash
# Start everything with Docker
./start-dev.sh docker

# Start only infrastructure (DB, Redis)
./start-dev.sh services

# View logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Stop all services
docker-compose down

# Reset database (⚠️ deletes data)
docker-compose down -v

# Database migrations
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

---

## 🔄 CI/CD & Deployment

### Supported Platforms

| Platform | Config File | Status |
|----------|-------------|--------|
| **Railway** | `railway.json` | ✅ Ready |
| **Render** | `render.yaml` | ✅ Ready |
| **Fly.io** | `fly.toml` | ✅ Ready |
| **Vercel** | `vercel.json` | ✅ Frontend |
| **Docker** | `Dockerfile` | ✅ Multi-stage |

### Environment-Specific Settings

```python
# Production settings (config.py)
DEBUG=false
ENVIRONMENT=production
ENABLE_DOCS=false
ENABLE_DEBUG_ERRORS=false
REQUIRE_AUTH=true
RATE_LIMIT_ENABLED=true
```

---

## 🗺 Roadmap

See [ENHANCEMENT_PLAN.md](./ENHANCEMENT_PLAN.md) for detailed roadmap.

### Current Phase: Foundation

- ✅ 8 analysis modules with parallel execution
- ✅ 72+ backend tests (scoring & report validation)
- ✅ Docker Compose deployment
- ✅ x402 payment integration
- ✅ PDF report generation

### Upcoming Features

- 🚧 **Phase 1:** Firecrawl integration (JS-capable scraping)
- 🚧 **Phase 2:** Serper.dev integration (Google Search/News)
- 🚧 **Phase 3:** Review aggregation (G2, Trustpilot, Capterra)
- 🚧 **Phase 4:** Professional scoring with confidence intervals

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript strict mode for frontend
- Add tests for new features
- Update documentation for API changes
- Ensure Docker builds pass

---

## 🔒 Security

- All API keys are validated at startup
- CORS configured per environment
- Rate limiting enabled by default
- JWT tokens for authentication
- SQL injection protection via SQLAlchemy ORM
- XSS protection via security headers middleware

### Security Headers

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2024 Brand Analytics

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Next.js](https://nextjs.org/) - React framework
- [OpenAI](https://openai.com/) - GPT-4o for AI analysis
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [Framer Motion](https://www.framer.com/motion/) - Animation library
- [RainbowKit](https://www.rainbowkit.com/) - Web3 wallet connection
- [x402 Protocol](https://x402.org/) - Web3 payment protocol

---

## 📞 Support

- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/xkonjin/brand-analytics/issues)
- 💡 **Feature Requests:** [GitHub Discussions](https://github.com/xkonjin/brand-analytics/discussions)
- 📧 **Email:** support@brand-analytics.dev

---

<p align="center">
  Built with ❤️ for startups and marketers
</p>

<!-- VISUAL_PLANNING_WORKFLOW:START -->
## Visual Planning Workflow

For non-trivial work, generate a visual artifact before or during implementation planning.

- `/generate-visual-plan` — visual implementation plan
- `/generate-web-diagram` — architecture/data-flow diagrams
- `/plan-review` — visual plan-vs-codebase risk review
- `/diff-review` — visual diff and architecture review

Artifacts are generated as HTML and typically opened from:

- `~/.agent/diagrams/`

When using `/fleetmax`, include the visual artifact path in handoff/report output.
<!-- VISUAL_PLANNING_WORKFLOW:END -->

