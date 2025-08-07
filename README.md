# FantasyPros Analytics

A **simple, clean data pipeline** for scraping FantasyPros rankings and serving them via API for analytics. Built for hobby-grade fantasy football analysis.

## 🎯 **What This Does**

- **Scrapes** FantasyPros consensus rankings (all positions, scoring types, weeks)
- **Stores** data in PostgreSQL with proper indexing
- **Serves** data via clean REST API  
- **Automates** data collection with simple scheduling
- **Containerized** for easy deployment

## 🏗️ **Simple Architecture**

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   FantasyPros   │───▶│   Scraper    │───▶│ PostgreSQL │
│     Website     │    │              │    │  Database  │
└─────────────────┘    └──────────────┘    └─────────────┘
                                                   │
┌─────────────────┐    ┌──────────────┐           │
│   Frontend      │◀───│  FastAPI     │◀──────────┘
│   Analytics     │    │   Server     │
└─────────────────┘    └──────────────┘
```

## 🚀 **Quick Start**

### **Option 1: Docker (Recommended)**

```bash
# Clone and start everything
git clone <repo>
cd fantasypros-scraper

# Start database + API + scheduler
docker-compose up -d

# Initialize database tables
docker-compose exec app python main.py init

# Run initial scraping
docker-compose exec app python main.py scrape --week 0

# View API at http://localhost:8000
```

### **Option 2: Local Development**

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Database (install PostgreSQL locally)
export DATABASE_URL="postgresql://user:pass@localhost:5432/fantasypros"

# Initialize
python main.py init

# Scrape data
python main.py scrape --week 0

# Start API server
python main.py server
```

## 📚 **Usage**

### **CLI Commands**

```bash
# Initialize database
python main.py init

# Manual scraping
python main.py scrape --week 0                    # All draft rankings
python main.py scrape --position QB --week 1      # QB week 1
python main.py scrape --position RB --scoring PPR # RB draft PPR

# Start services
python main.py server                             # API server
python main.py scheduler                          # Automated scraping

# Check status
python main.py status
```

### **API Endpoints**

```bash
# Get rankings
GET /rankings/QB?week=0&scoring=STD              # QB draft standard
GET /rankings/RB?week=1&scoring=PPR&limit=50     # RB week 1 PPR

# Player data
GET /players/Josh%20Allen                        # Player history

# Metadata
GET /positions                                   # Available positions
GET /weeks?year=2025                            # Available weeks
GET /stats                                       # System stats

# Manual scraping (admin)
POST /admin/scrape/draft                         # Trigger draft scrape
POST /admin/scrape/weekly?week=1                 # Trigger weekly scrape
```

## 🗄️ **Data Schema**

**Simple, focused tables:**

- **`players`** - Player information
- **`rankings`** - All ranking data with proper indexing
- **`scraping_logs`** - Simple job tracking

**Key fields for analytics:**
- `rank_ecr` - Expert consensus ranking
- `rank_std` - Standard deviation (for tier generation)
- `rank_min/max` - Expert range
- `tier` - Generated tier (for Boris Chen style analysis)

## ⚙️ **Configuration**

Set via environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Application  
DEBUG=true
PORT=8000
CURRENT_YEAR=2025

# Scraping
SCRAPING_DELAY=1.0
MAX_RETRIES=3
```

## 🔄 **Automated Scheduling**

- **Draft Season** (July-August): Every 6 hours
- **Regular Season** (September+): 3x daily (8am, 2pm, 8pm)
- **Health checks**: Every 30 minutes

## 📊 **Next Steps: Analytics**

This pipeline provides **clean data** for building:

1. **Tier Generation** (Boris Chen style using `rank_std`)
2. **Player Movement Tracking** (week-over-week changes)
3. **Interactive Dashboards** (React frontend)
4. **Trade Analysis** (player value trends)

## 🐳 **Production Deployment**

### **Docker Compose (Simple)**
- Use provided `docker-compose.yml`
- Update environment variables
- Use external PostgreSQL for production

### **Cloud Deployment**
- Deploy containers to any cloud platform
- Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- Set proper environment variables

## 🛠️ **Development**

**Project Structure:**
```
app/
├── config.py              # Simple configuration
├── database/
│   └── models.py          # Clean SQLAlchemy models
├── scraper/
│   └── fantasypros.py     # FantasyPros scraper
├── api/
│   └── server.py          # FastAPI server
└── scheduler.py           # Simple scheduling

main.py                    # CLI entry point
requirements.txt           # Minimal dependencies
Dockerfile                 # Container setup
docker-compose.yml         # Local development
```

**Philosophy:**
- ✅ **Simple & Clean** - No overengineering
- ✅ **Modular** - Easy to understand and modify  
- ✅ **DRY** - Reusable components
- ✅ **Focused** - Built for analytics, not enterprise scale

---

**Perfect for hobby-grade fantasy football analytics! 🏈** 