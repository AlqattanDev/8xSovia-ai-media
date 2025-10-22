# 8xSovia - AI Media Platform

A comprehensive platform for organizing and discovering connections in AI-generated media from Grok/xAI.

## Projects

### 1. Media Gallery (FastAPI + PostgreSQL)
Traditional media management with collections, search, and filtering.

### 2. Smart Video Chain Finder (FastAPI + Next.js)
**NEW!** AI-powered tool that discovers meaningful video sequences using multi-modal analysis.

## Quick Start

### Smart Video Chain Finder (Recommended)

**Prerequisites:**
```bash
pip install fastapi uvicorn open-clip-torch torch opencv-python pillow imagehash numpy scenedetect
cd video-chains-modern && npm install
```

**Start:**
```bash
# Terminal 1 - Backend (port 8001)
cd video-chains
python app.py

# Terminal 2 - Frontend (port 3000)
cd video-chains-modern
npm run dev
```

**Visit:** http://localhost:3000

**Features:**
- Semantic video understanding with CLIP
- Multi-modal scoring (frame, semantic, color, motion)
- Smart chain discovery with quality scores
- Modern Next.js UI with real-time previews

### Media Gallery (Legacy)

**Prerequisites:**
- Python 3.9+, PostgreSQL 14+, Redis

**Start:**
```bash
./start.sh  # Auto-setup and start on http://localhost:8000
```

**Stop:**
```bash
./stop.sh
```

### Manual Startup

If you prefer manual control:

```bash
# Start services
brew services start postgresql@14
brew services start redis

# Setup database
createdb media_gallery
psql postgres -c "CREATE USER gallery_user WITH PASSWORD 'password';"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE media_gallery TO gallery_user;"

# Install dependencies
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
8xSovia/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   │   ├── main.py      # API endpoints
│   │   ├── models.py    # SQLAlchemy models
│   │   ├── schemas.py   # Pydantic schemas
│   │   ├── database.py  # DB connection
│   │   └── config.py    # Configuration
│   ├── alembic/         # Database migrations
│   └── requirements.txt
├── js/                  # Frontend modules
├── https_/              # Downloaded media files
├── archive/             # Backups and old files
├── index.html           # Main frontend
├── start.sh             # Startup script
├── stop.sh              # Stop script
├── bulk_download_from_json.py  # Media download utility
└── alawii96.json        # Sample data for testing
```

## Features

- **Media Gallery**: Browse images and videos with infinite scroll
- **Smart Collections**: Auto-populated collections based on filters
- **Comparison Mode**: Compare up to 4 items side-by-side
- **Filter Presets**: Save and load custom filter combinations
- **Import System**: Bulk import from JSON with automatic file mapping
- **Similar Items**: TF-IDF based content similarity
- **Advanced Search**: Full-text search in prompts and metadata

## API Documentation

Once started, visit http://localhost:8000/docs for interactive API documentation.

## Configuration

Edit `.env` to customize:
- Database connection
- Redis connection
- API settings
- CORS origins
- Storage paths

## Development

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Import Media

Use the import modal in the frontend or the bulk download script:

```bash
python bulk_download_from_json.py --json-file your_data.json
```

## Documentation

- `CLAUDE.md` - Detailed project documentation for AI assistants
- `FEATURES_IMPLEMENTED.md` - Feature list and implementation details
- `QUICK_START.md` - Original quick start guide

## License

Private project
