# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

8xSovia is an AI Media Gallery application for organizing and browsing AI-generated images and videos from Grok/xAI. It features a FastAPI backend with PostgreSQL + Redis, and a vanilla JavaScript frontend with advanced UI capabilities.

## Running the Application

### Backend Setup
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run migrations (PostgreSQL must be running)
alembic upgrade head

# Start development server (auto-reload enabled)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
Open `index.html` directly in a browser, or serve via:
```bash
python -m http.server 8080
```

The frontend connects to `http://localhost:8000` by default (configured in `index.html` ~line 2251).

### Database Migrations
```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

## Architecture

### Backend (FastAPI + SQLAlchemy 2.0)

**Core Structure:**
- `app/main.py` - FastAPI application with all API endpoints (~1300 lines)
- `app/models.py` - SQLAlchemy models (User, MediaPost, ChildPost, Collection, CollectionItem, UserPreference)
- `app/schemas.py` - Pydantic request/response validation schemas
- `app/database.py` - Async database session management
- `app/config.py` - Pydantic settings (loads from `.env`)

**Data Model:**
- **MediaPost** (parent) ← **ChildPost** (many) - Core relationship for parent posts and their generated videos
- **Collection** ← **CollectionItem** - Many-to-many through table for organizing media
- **User** - Owns all posts, collections, and preferences
- **UserPreference** - Stores user UI preferences in JSONB column

**Key Features:**
- Async SQLAlchemy with asyncpg driver
- Redis caching (5-min TTL) for stats and model lists
- JSONB columns for flexible metadata storage
- Comprehensive indexes for query performance

**Import System (NEW):**
- `/api/import` - Bulk import from JSON with automatic URL→local path mapping
- `/api/check-existing` - Batch check for existing post IDs
- `url_to_local_path()` helper converts Grok URLs to local file paths in `https_/` directory structure
- Handles timezone-aware datetime conversion for PostgreSQL compatibility

**Similarity Algorithm:**
- TF-IDF vectorization using scikit-learn
- Cosine similarity for content matching
- Metadata boosting (1.5x same model, 1.2x same mode)
- Endpoint: `/api/media/{id}/similar?limit=6`

### Frontend (Vanilla JavaScript)

**Single File Architecture:** All code in `index.html` (~3800 lines total)
- Lines 1-1600: HTML structure + CSS
- Lines 1600-2600: Modals (detail view, comparison, collections, import)
- Lines 2600-3800: JavaScript

**State Management:**
- Global state variables for current filters, selected items, collections
- URL state sync for filters (updates browser history)
- LocalStorage for user preferences (view mode, density, sort)

**Key Components:**
- **Infinite Scroll** - Intersection Observer triggers at 200px before bottom
- **Hover Video Preview** - Lazy loading + 100ms debounce
- **Comparison Mode** - Select up to 4 items for side-by-side view
- **Collections Sidebar** - Regular + Smart collections with filter preview
- **Filter Presets** - Save/load filter combinations to database
- **Import Modal** - 5-step wizard for JSON import with download list generation

**API Communication:**
- All API calls use `fetch()` with proper error handling
- Toast notifications for user feedback
- Caching for similar items and collection previews

## Important File Paths

### Media Storage
Downloaded media files are organized by URL structure:
```
/Users/alialqattan/Downloads/8xSovia/https_/
├── assets.grok.com/users/.../generated_video.mp4
├── imagine-public.x.ai/imagine-public/share-videos/*.mp4
└── images-public.x.ai/xai-images-public/imagine/share-videos/*.mp4
```

The import system automatically maps URLs like:
- `https://assets.grok.com/users/...` → `/Users/alialqattan/Downloads/8xSovia/https_/assets.grok.com/users/...`

### Database Backups
Located in `archive/` directory with timestamped SQLite backups.

## Database Schema Notes

### Important Indexes
- `media_posts`: Indexed on `user_id`, `create_time`, `media_type`, `model_name`, `like_status`
- `child_posts`: Indexed on `parent_post_id`, `mode`, `model_name`
- **Limitation**: `original_prompt` fields CANNOT be indexed due to PostgreSQL B-tree size limits

### JSONB Columns
- `extra_metadata` - Flexible storage for future fields
- `smart_filters` - Collection filter criteria (model, mode, keywords)
- `preferences` - User UI settings (viewMode, density, sortOption)

### Datetime Handling
- All timestamps are stored as `TIMESTAMP WITHOUT TIME ZONE` (naive UTC)
- Import system strips timezone info from ISO 8601 timestamps
- Frontend displays dates using JavaScript `toLocaleString()`

## API Endpoint Patterns

### Pagination
All list endpoints support:
- `skip` - Offset (default: 0)
- `limit` - Page size (default: 50, max: 100)

### Filtering
`/api/media` supports:
- `type` - Filter by media type (all/image/video)
- `liked` - Filter by like status (all/true/false)
- `model` - Filter by AI model name
- `mode` - Filter by generation mode (all/normal/custom)
- `search` - Full-text search in prompts
- `sort` - Sort order (date_desc/date_asc/model/type)

### Collections
- Regular collections: Manual item management
- Smart collections: Auto-populated based on `smart_filters` JSONB criteria

### Import Workflow
1. Upload JSON file in frontend
2. Frontend calls `/api/check-existing` with post IDs (batch)
3. Display preview stats (new vs existing)
4. Generate download URLs for missing media
5. User downloads media files
6. Frontend calls `/api/import` to insert new posts
7. Backend converts URLs to local paths if files exist

## Redis Caching Strategy

Cached keys:
- `stats` - Gallery statistics (total items, videos, likes)
- `models` - List of AI models
- `similar:{post_id}` - Similar items results

Cache invalidation:
- Cleared on: post creation, update, deletion, like toggle, import
- TTL: 5 minutes (configurable in `config.py`)

## Frontend State Synchronization

**Filter State → URL:**
```javascript
updateUrlState() // Pushes filter changes to browser history
restoreStateFromUrl() // Reads filters from URL params on load
```

**User Preferences → LocalStorage → Database:**
1. UI changes trigger `saveUserPreferences()`
2. Saved to localStorage for instant persistence
3. Debounced API call updates database
4. On load: Database preferences override localStorage

## Known Limitations

1. **Authentication**: Currently uses first user from database. No login system implemented.
2. **File Upload**: No direct file upload. Users must download media externally and use import system.
3. **Large Prompts**: Cannot be indexed in PostgreSQL. Search relies on sequential scans.
4. **TF-IDF Performance**: Similar items calculation is CPU-intensive for large datasets. Consider background job processing for production.
5. **Import Timezone**: Assumes all imported timestamps are UTC. No timezone conversion.

## Development Patterns

### Adding New Filters
1. Add query parameter to `/api/media` endpoint in `main.py`
2. Add filter logic to SQLAlchemy query
3. Add UI control in frontend filters section
4. Update `applyFilters()` and `updateUrlState()` in JavaScript
5. Add to smart collection filter options if applicable

### Adding New Fields to Models
1. Create Alembic migration: `alembic revision --autogenerate -m "add_field"`
2. Update Pydantic schemas in `schemas.py`
3. Update frontend rendering in `createGalleryItem()` or modal templates
4. Consider JSONB `extra_metadata` for optional/experimental fields

### Testing Import System
Use `alawii96.json` in project root as test data (82 posts with videos/images).

## Performance Considerations

- **Lazy Loading**: Frontend uses Intersection Observer for infinite scroll and video preview
- **Debouncing**: Smart collection preview (500ms), hover events (100ms)
- **Batch Operations**: Import uses batch post ID checking instead of individual requests
- **Connection Pooling**: PostgreSQL pool size: 20, max overflow: 40 (adjust in `config.py`)
- **Redis Caching**: Reduces database load for frequently accessed data

## API Documentation

Full interactive docs available at: `http://localhost:8000/docs` (auto-generated by FastAPI)
