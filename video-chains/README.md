# 🧠 Smart Video Chain Finder

AI-powered video chain discovery tool that automatically finds and connects video clips into meaningful sequences using frame similarity matching and semantic understanding.

## What It Does

1. **Scans** all your videos (5,453 videos analyzed!)
2. **Extracts** first and last frames + AI embeddings
3. **Finds chains** where videos flow together naturally
4. **Shows diversity** - different characters and scenes
5. **Rates quality** - 0-100% match scores
6. **Merges** chains into longer videos

## Quick Start

### Backend Setup

```bash
cd video-chains

# Install dependencies
pip install -r requirements.txt

# Start the API server
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd video-chains-modern

# Install dependencies
npm install

# Start development server
npm run dev
```

The UI will be available at `http://localhost:3000`

## Features

### Core Capabilities
- ✨ **Smart Chain Discovery**: Finds videos that flow together naturally
- 🎯 **Diversity Sampling**: Shows chains with different starting videos/characters
- ⭐ **Quality Scoring**: Rates chain quality 0-100% based on frame similarity
- ▶️ **Video Preview**: Play entire chains sequentially with timeline
- 🔍 **Unique Filtering**: Filter to show only unique starting frames
- 🎬 **Hover Previews**: See videos on hover
- 🔗 **One-Click Merging**: Combine chains into single videos

### Technologies
- **Backend**: FastAPI (Python 3.13)
- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS 4
- **AI/ML**: CLIP (OpenAI) for semantic similarity
- **Video Processing**: OpenCV, imagehash, ffmpeg

## Project Structure

```
video-chains/
├── app.py                          # FastAPI backend with chain discovery
├── video_analyzer.py               # Basic frame-based analysis
├── video_analyzer_smart.py         # AI-powered semantic analysis
├── utils/
│   └── error_handler.py            # Centralized error handling
├── _legacy_ui_archive/             # Original HTML UI (archived)
├── static/                         # Static assets
├── logs/                           # Application logs
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── CHANGELOG.md                    # Detailed progress documentation

video-chains-modern/
├── src/
│   ├── app/
│   │   ├── page.tsx                # Home page with stats
│   │   └── discover/
│   │       └── page.tsx            # Main chain discovery page
│   ├── components/
│   │   ├── ChainPreviewModal.tsx   # Video preview modal
│   │   └── HelpModal.tsx           # Help/tutorial modal
│   ├── types/
│   │   └── chain.ts                # Shared TypeScript types
│   ├── config/
│   │   └── api.ts                  # API configuration
│   └── utils/
│       └── chainUtils.ts           # Quality utilities
└── package.json
```

## How It Works

### 1. Video Analysis
- Extracts first and last frames from each video
- Generates perceptual hashes using imagehash
- Optionally: CLIP embeddings for semantic understanding

### 2. Chain Discovery
- Uses Depth-First Search (DFS) to find connected videos
- Matches last frame of video A with first frame of video B
- Filters by hamming distance threshold (lower = more similar)

### 3. Diversity Sampling ⭐ NEW
- Samples across entire dataset (1.3M+ chains)
- Groups chains by first frame hash
- Returns best chain from each unique starting point
- Result: **Maximum variety** in displayed chains

### 4. Quality Scoring
- Calculates frame similarity between consecutive videos
- Score = 1 - (hamming_distance / 64)
- Displays color-coded quality badges:
  - 🟢 Green (≥80%): Excellent
  - 🟡 Yellow (≥60%): Good
  - 🟠 Orange (<60%): Fair

## API Endpoints

### GET `/api/info`
Get API status and video count

### GET `/api/chains?min_length=2&threshold=15`
Find video chains using frame matching
- **min_length**: Minimum videos in chain (default: 2)
- **threshold**: Hamming distance threshold (default: 15)

### GET `/api/chains/smart?min_score=0.6&min_length=2`
Find chains using AI semantic matching (requires SMART mode)
- **min_score**: Minimum quality score 0-1 (default: 0.6)
- **min_length**: Minimum videos in chain (default: 2)

### GET `/api/video/{path}`
Serve video file by path

### POST `/api/merge`
Merge multiple videos into a single file

## Configuration

### Video Directory
Update the `VIDEO_DIR` path in `app.py`:

```python
VIDEO_DIR = "/path/to/your/videos"
```

### Cache Files
- `video_data.json` - Basic frame hashes
- `video_data_smart.json` - CLIP embeddings + metadata
- Response caching for faster subsequent requests

## Performance

### First-Time Analysis
- **5,453 videos**: ~5-10 minutes
- Cached for instant future access

### Chain Discovery
- **First request**: 2-5 seconds (computes diversity sampling)
- **Cached requests**: <100ms

### Optimization Tips
- Use quality threshold 75-85% for faster results
- Lower thresholds (<60%) = slower but more chains
- Cache is invalidated on rescan

## Recent Improvements

See [CHANGELOG.md](CHANGELOG.md) for detailed progress documentation.

### Version 2.1.0 Highlights
✅ **Diversity sampling** (1 → 4 unique starting frames)
✅ **Quality score calculations** (real percentages, not NaN)
✅ **Code deduplication** (eliminated 45+ duplicate lines)
✅ **Centralized error handling**
✅ **Shared TypeScript types** and utilities
✅ **Variant count badges** (+99 variants indicator)
✅ **Video preview modal** with full playback controls

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Detailed progress and improvements
- [QUICK_START_V2.md](QUICK_START_V2.md) - Extended setup guide
- [SMART_FEATURES.md](SMART_FEATURES.md) - AI features documentation
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md) - Data structure design

## Interactive API Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

Proprietary - Ali Alqattan

## Credits

- Development: Claude (Anthropic AI)
- Project Owner: Ali Alqattan
- Framework: FastAPI, Next.js
- AI Models: OpenAI CLIP

---

*Built with AI-assisted development using Claude Code*
