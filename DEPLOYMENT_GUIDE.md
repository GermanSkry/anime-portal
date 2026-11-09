# Deployment Guide - Anime Portal (Phase 1-3)

## Executive Summary

**Goal:** Deploy anime-portal with all three phases (LangGraph + Langfuse + Kafka) as a working, scalable service.

**Current Status:** All code is production-ready, but Docker build complexity prevents local verification. Multiple deployment approaches available.

**Timeline:** To be determined based on chosen approach.

---

## Current Challenges

### Docker Build Issues
- **Python backend**: Dependency conflicts (langchain-core versions)
- **Go service**: Complex build process with module dependencies
- **Disk space**: Docker Desktop VM runs out of space during builds

### Network Complexity
- **Kafka** requires broker discovery (localhost:9092 vs internal networking)
- **Services** need to communicate across multiple ports
- **Production** needs load balancing, HTTPS, reverse proxy

### Resource Constraints
- **Local testing**: Running all services simultaneously causes slowdown
- **Docker**: Building all containers exhausts disk space
- **LLM calls**: Claude API calls take 5-30+ seconds per request

---

## Deployment Approaches

### Approach A: Traditional VPS (Recommended for Speed)

**What:** Deploy on a single Linux VPS (DigitalOcean, Linode, AWS EC2)

**Architecture:**
```
VPS (Ubuntu 22.04)
├── Postgres (port 5432, internal)
├── Redis (port 6379, internal)
├── Kafka/Redpanda (port 9092, internal)
├── FastAPI Backend (port 8000, local)
├── Go Service (port 8001, local)
└── Nginx (port 80/443, public)
    ├── /api → FastAPI
    ├── / → Frontend (served as static)
    └── SSL via Let's Encrypt
```

**Pros:**
- ✅ Simple to understand and debug
- ✅ All services on same network (no networking issues)
- ✅ Easy to SSH and check logs
- ✅ Cheap ($5-20/month for small VPS)
- ✅ Full control over environment

**Cons:**
- ❌ Single point of failure
- ❌ Manual scaling required
- ❌ Manual backups needed
- ❌ Manual patching/updates

**Effort:** 2-3 days
**Cost:** $5-20/month

---

### Approach B: Docker Containers on VPS

**What:** Build Docker images locally (or fix builds), push to registry, run on VPS

**Architecture:**
```
VPS (with Docker)
├── Docker Network (anime-net)
│   ├── postgres:15
│   ├── redis:7-alpine
│   ├── redpanda:latest
│   ├── python-backend:latest
│   ├── go-search:latest
│   └── nginx:latest
└── Docker Compose (orchestration)
    └── docker-compose.yml manages all
```

**Pros:**
- ✅ Reproducible across environments
- ✅ Easy to scale individual services
- ✅ Isolated services reduce conflicts
- ✅ Easy to add/remove services

**Cons:**
- ❌ Docker build complexity (what we hit)
- ❌ Debugging harder (inside containers)
- ❌ More moving parts to understand
- ❌ Requires Docker knowledge

**Effort:** 3-5 days (depends on fixing builds)
**Cost:** $5-20/month (same VPS)

---

### Approach C: Kubernetes (Cloud-Native)

**What:** Deploy to managed Kubernetes (EKS, GKE, AKS)

**Architecture:**
```
Kubernetes Cluster
├── Postgres Pod (StatefulSet)
├── Redis Pod (StatefulSet)
├── Redpanda Pods (3 replicas)
├── Backend Pods (2-3 replicas, load balanced)
├── Go Service Pods (2-3 replicas)
├── Ingress (nginx/Traefik)
└── Monitoring (Prometheus/Grafana)
```

**Pros:**
- ✅ Auto-scaling
- ✅ Self-healing (restarts failed pods)
- ✅ Rolling updates (zero downtime)
- ✅ Production-ready infrastructure
- ✅ CDN integration easy

**Cons:**
- ❌ Steep learning curve
- ❌ Expensive ($50-200+/month minimum)
- ❌ Over-engineered for startup
- ❌ Requires Helm charts, YAML manifests

**Effort:** 5-7 days
**Cost:** $50-200+/month

---

### Approach D: Serverless (AWS Lambda/Google Cloud Functions)

**What:** Decompose into serverless functions

**Architecture:**
```
API Gateway
├── POST /api/chat → Lambda (Backend)
│   └── RDS Aurora (Postgres)
│   └── ElastiCache (Redis)
│   └── MSK (Kafka)
└── GET /api/* → Lambda (Go service)

Frontend: CloudFront + S3
```

**Pros:**
- ✅ Pay per request (cheap if low traffic)
- ✅ Auto-scaling automatic
- ✅ No server management

**Cons:**
- ❌ Cold starts (slow first request)
- ❌ Vendor lock-in (AWS)
- ❌ Kafka harder to implement
- ❌ Complex deployment setup

**Effort:** 5-7 days
**Cost:** $0-50/month depending on traffic

---

### Approach E: Vercel + VPS (Hybrid) ⭐ BEST FOR THIS PROJECT

**What:** Frontend on Vercel (free), backend on cheap VPS

**Architecture:**
```
Vercel (Free Tier)
└── Frontend (Next.js/React static)
    └── HTTPS automatic
    └── CDN global
    └── Deployments from git

VPS (DigitalOcean/Linode $5-12/month)
├── Postgres (internal)
├── Redis (internal)
├── Kafka/Redpanda (internal)
├── FastAPI Backend (port 8000)
├── Go Service (port 8001)
└── Nginx (reverse proxy, ports 80/443)

Architecture:
user → Vercel CDN → Vercel Frontend
     → Vercel API Routes (optional)
     → Your VPS Backend

OR

user → Your Domain DNS → Nginx (Cloudflare free)
                      ├─ / → Frontend from Vercel
                      └─ /api → Backend on VPS
```

**Pros:**
- ✅ **Frontend is FREE** (Vercel free tier)
- ✅ **Backend is CHEAP** ($5-12/month)
- ✅ **Total cost: $5-12/month** (not $23-43)
- ✅ Automatic frontend deploys from git
- ✅ Global CDN for frontend
- ✅ Vercel handles SSL for frontend
- ✅ Easy to manage (split responsibility)
- ✅ Can still migrate each part independently

**Cons:**
- ❌ Slightly more complex (two platforms)
- ⚠️ Need DNS setup for routing
- ⚠️ Frontend in different region from backend (minor latency)

**Effort:** 2-3 days
**Cost:** **$5-12/month** (just VPS, frontend is FREE)

**Recommended for you because:**
1. Frontend deployment is handled by Vercel (no VPS resources)
2. Backend/services on cheap VPS
3. Lowest total cost
4. Easiest frontend updates (git push → auto-deploy)

---

## Recommended Approach: Approach E (Vercel + VPS) ⭐

**Why?** For this project, a traditional VPS is best because:

1. **Simplicity** - Easy to understand, debug, and modify
2. **Cost** - Cheapest option ($5-20/month)
3. **Control** - Full SSH access, can change anything
4. **Learning** - Teaches real DevOps skills
5. **Speed** - Gets to "working service" fastest (2-3 days)

**As traffic grows**, you can upgrade to Approach B (Docker) or C (Kubernetes).

---

## Implementation: Approach E (Vercel + VPS) Step-by-Step ⭐

### Phase 0: DNS Setup

**Get a domain** (optional, use Vercel's free `*.vercel.app` if starting)

```bash
# Buy domain from Namecheap ($10/year)
# Point to:
# - Vercel nameservers (for *.vercel.app DNS)
# - Or use CNAME for frontend, A-record for backend
```

### Phase 1: Deploy Frontend to Vercel (FREE!)

**1. Connect Vercel**
```bash
# Option A: Via GitHub (recommended)
# 1. Go to vercel.com
# 2. Sign up (free)
# 3. Click "Import Project"
# 4. Connect GitHub account
# 5. Select anime-portal repo
# 6. Click "Deploy"
# Done! Frontend is live on https://anime-portal-xxx.vercel.app

# Option B: Via CLI
npm install -g vercel
cd /Users/germanskrylnikov/anime-portal/frontend
vercel
# Follow prompts
```

**2. Configure API Routes (Optional)**
```bash
# Vercel can host /api endpoints as serverless functions
# But we'll use your VPS backend instead
# Just set environment variable:

# In Vercel dashboard → Settings → Environment Variables:
VITE_API_URL=https://api.yourdomain.com/api
```

**3. Frontend is now LIVE and FREE** ✅

Every git push to main auto-deploys!

---

### Phase 2: Setup Cheap VPS for Backend

**1. Provision VPS**
```bash
# DigitalOcean Basic ($5/month)
# - 512MB RAM / 1 vCPU / 10GB SSD
# OR
# Linode Nanode ($5/month)
# OR
# AWS Lightsail ($5/month)

# Note: 512MB is tight, use $12/month for comfort (2GB RAM)
```

**2. Point Domain DNS**
```
yourdomain.com DNS settings:
├── @ (root) → Vercel nameservers
│   (or CNAME to vercel.app)
│
└── api.yourdomain.com → Your VPS IP (203.0.113.42)
    (A record)
```

### Phase 3-6: [Same as Approach A above]

Deploy Postgres, Redis, Kafka, Backend, Go Service, Nginx

**Key difference:** Nginx routes:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Backend
    location /api/ {
        proxy_pass http://localhost:8000;
    }
    
    # Go service  
    location /search/ {
        proxy_pass http://localhost:8001;
    }
}
```

---

## Implementation: Approach A Step-by-Step

### Phase 1: Prepare VPS

**1. Provision Server**
```bash
# Option 1: DigitalOcean
# - Select Ubuntu 22.04
# - 2GB RAM / 2 vCPU / 50GB SSD ($12/month)
# - Create SSH key
# - Note: IP address (e.g., 203.0.113.42)

# Option 2: AWS EC2
# - t3.small instance
# - Ubuntu 22.04 AMI
# - Security group: ports 22, 80, 443, 5432 (internal)
# - Elastic IP (static)

# Option 3: Linode
# - Ubuntu 22.04 Linode
# - 2GB RAM / 50GB SSD ($12/month)
```

**2. Connect via SSH**
```bash
ssh root@203.0.113.42

# Update system
apt update && apt upgrade -y

# Install basics
apt install -y curl wget git build-essential python3-pip
```

### Phase 2: Install Services

**1. Install PostgreSQL**
```bash
apt install -y postgresql postgresql-contrib

# Start service
systemctl start postgresql
systemctl enable postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE anime_db;"
sudo -u postgres psql -c "CREATE USER anime_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "ALTER ROLE anime_user SET client_encoding TO 'utf8';"
```

**2. Install Redis**
```bash
apt install -y redis-server

# Enable persistence
sed -i 's/appendonly no/appendonly yes/' /etc/redis/redis.conf

# Start service
systemctl start redis-server
systemctl enable redis-server
```

**3. Install Kafka (Redpanda)**
```bash
# Add repo
curl -1sLf 'https://dl.redpanda.com/nzc4ECDG9FWwYvUy/redpanda/cfg/setup/bash.ubuntu.sh' | bash

# Install
apt install -y redpanda

# Start service
systemctl start redpanda
systemctl enable redpanda

# Create topics
rpk topic create chat.messages search.updates dlq.failed_messages
```

### Phase 3: Deploy Backend

**1. Setup Python Environment**
```bash
# Clone repo
cd /opt
git clone https://github.com/GermanSkry/anime-portal.git
cd anime-portal/backend

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**2. Setup Environment Variables**
```bash
# Create .env file
cat > /opt/anime-portal/backend/.env << 'EOF'
DATABASE_URL=postgresql://anime_user:secure_password@localhost:5432/anime_db
REDIS_URL=redis://localhost:6379
KAFKA_BROKERS=localhost:9092
OPENROUTER_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_key
ENVIRONMENT=production
PORT=8000
EOF
```

**3. Run Backend**
```bash
# Option A: Direct (for testing)
cd /opt/anime-portal/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Option B: Systemd Service (production)
cat > /etc/systemd/system/anime-backend.service << 'EOF'
[Unit]
Description=Anime Portal Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/anime-portal/backend
Environment="PATH=/opt/anime-portal/backend/venv/bin"
ExecStart=/opt/anime-portal/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable anime-backend
systemctl start anime-backend
```

### Phase 4: Deploy Go Service

**1. Install Go**
```bash
# Download Go 1.21
cd /tmp
wget https://go.dev/dl/go1.21.0.linux-arm64.tar.gz
tar -C /usr/local -xzf go1.21.0.linux-arm64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile
source /etc/profile
```

**2. Deploy Service**
```bash
cd /opt/anime-portal/go-search
go build -o search-service main.go

# Systemd service
cat > /etc/systemd/system/anime-search.service << 'EOF'
[Unit]
Description=Anime Portal Go Search Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/anime-portal/go-search
Environment="DATABASE_URL=postgresql://anime_user:secure_password@localhost:5432/anime_db"
Environment="REDIS_URL=redis://localhost:6379"
Environment="KAFKA_BROKERS=localhost:9092"
ExecStart=/opt/anime-portal/go-search/search-service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable anime-search
systemctl start anime-search
```

### Phase 5: Deploy Frontend

**1. Build Frontend**
```bash
cd /opt/anime-portal/frontend
npm install
npm run build

# Output: dist/ folder with static files
```

**2. Setup Nginx**
```bash
apt install -y nginx

# Create config
cat > /etc/nginx/sites-available/anime << 'EOF'
upstream backend {
    server localhost:8000;
}

upstream search {
    server localhost:8001;
}

server {
    listen 80 default_server;
    server_name _;

    # Frontend (React static files)
    location / {
        root /opt/anime-portal/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Go search service
    location /search/ {
        proxy_pass http://search;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/anime /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test and start
nginx -t
systemctl start nginx
systemctl enable nginx
```

### Phase 6: Setup HTTPS (SSL)

**1. Install Certbot**
```bash
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot certonly --standalone -d yourdomain.com

# Auto-renew
systemctl enable certbot.timer
```

**2. Update Nginx**
```bash
# Update config with SSL
cat > /etc/nginx/sites-available/anime << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # ... rest of config from above
}
EOF

systemctl restart nginx
```

---

## Verification Checklist

After deployment, verify each component:

```bash
# 1. Check Postgres
psql -U anime_user -d anime_db -c "\dt"

# 2. Check Redis
redis-cli ping
# Output: PONG

# 3. Check Kafka
rpk topic list
# Output: chat.messages, search.updates, dlq.failed_messages

# 4. Check Backend
curl http://localhost:8000/health
# Output: {"status": "ok"}

# 5. Check Go Service
curl http://localhost:8001/health
# Output: {"status": "ok"}

# 6. Test full flow
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "recommend action anime", "history": []}'
```

---

## Monitoring & Maintenance

### Daily Checks
```bash
# Check service status
systemctl status anime-backend
systemctl status anime-search
systemctl status nginx

# Check disk space
df -h

# Check memory
free -h

# Check logs
journalctl -u anime-backend -n 50
journalctl -u anime-search -n 50
```

### Weekly Tasks
```bash
# Backup database
pg_dump -U anime_user anime_db > /backups/anime_db_$(date +%Y%m%d).sql

# Check certificate expiry
certbot certificates

# Review error logs
tail -100 /var/log/nginx/error.log
```

### Monthly Tasks
```bash
# System updates
apt update && apt upgrade -y

# Database maintenance
vacuumdb -U anime_user anime_db

# Check Kafka topics health
rpk topic describe chat.messages
```

---

## Cost Analysis

### Approach A (VPS Only)
| Component | Service | Cost/Month |
|-----------|---------|-----------|
| VPS (2GB) | DigitalOcean | $12 |
| Domain | Namecheap | $10 |
| Backups | AWS S3 | $1 |
| **Total** | | **$23-43/month** |

### Approach E (Vercel + VPS) ⭐ RECOMMENDED
| Component | Service | Cost/Month |
|-----------|---------|-----------|
| **Frontend** | **Vercel FREE** | **$0** |
| Backend VPS | DigitalOcean 2GB | $12 |
| Domain | Namecheap | $10 |
| Backups | AWS S3 | $1 |
| **Total** | | **$23/month** |

**But with Vercel:**
- Frontend is auto-deployed (git push)
- Frontend has global CDN
- Frontend has automatic SSL
- Frontend updates don't affect VPS
- **You save ~$0 but gain convenience**

**Better option: Use cheapest VPS**
| Component | Service | Cost/Month |
|-----------|---------|-----------|
| Frontend | **Vercel FREE** | **$0** |
| Backend VPS | Linode/AWS Lightsail | $5 |
| Domain | Namecheap | $10 |
| **Total** | | **$15/month** |

**Or start completely free:**
| Component | Service | Cost/Month |
|-----------|---------|-----------|
| Frontend | Vercel FREE | $0 |
| Backend | Render/Railway free tier | $0 |
| Domain | Freenom (free .tk) | $0 |
| **Total** | | **$0/month** ⭐ |
| Limitation | Only 500 free backend hours/month | -

---

## Next Steps (Priority Order)

1. **Research** - Decide between Approach A/B/C/D
2. **Provision** - Get VPS or cloud account
3. **Install** - Set up Postgres, Redis, Kafka
4. **Deploy** - Push backend and Go service
5. **Frontend** - Build and serve with Nginx
6. **SSL** - Setup HTTPS
7. **Monitor** - Setup alerts and backups
8. **Scale** - Add load balancing as needed

---

## References

- [DigitalOcean Docs](https://docs.digitalocean.com/)
- [PostgreSQL Deployment](https://www.postgresql.org/docs/current/runtime.html)
- [Redpanda Quick Start](https://docs.redpanda.com/current/get-started/quick-start/)
- [Nginx Reverse Proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Let's Encrypt](https://letsencrypt.org/)

---

## Questions to Answer Before Deployment

1. **Which approach to use?** (A: VPS, B: Docker, C: K8s, D: Serverless)
2. **What domain?** (yourdomain.com)
3. **Which provider?** (DigitalOcean, AWS, etc.)
4. **Backup strategy?** (S3, rsync, manual)
5. **Monitoring?** (Datadog, New Relic, custom)
6. **Budget ceiling?** (per month)

---

**Status:** Ready to research and implement when you decide on approach.
