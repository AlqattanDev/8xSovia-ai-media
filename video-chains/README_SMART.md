# 🧠 Smart Video Chain Finder

**AI-powered video chain discovery with semantic understanding**

Transform your collection of AI-generated video fragments into coherent narrative sequences using cutting-edge computer vision and deep learning.

## 🆕 Version 2.0: Smart Mode

The Video Chain Finder now features **two modes**:

### 📊 Basic Mode (v1.0)
- Frame-based matching using perceptual hashes
- Fast and lightweight
- Works with minimal dependencies

### 🧠 Smart Mode (v2.0) - NEW!
- **Multi-modal chain scoring** combining 4 signals:
  - Frame similarity (perceptual hashing)
  - **Semantic similarity (CLIP embeddings)** 🆕
  - **Color continuity (histogram matching)** 🆕
  - **Motion continuity (action detection)** 🆕
- **Scene detection** for better transitions
- **Quality scoring** (0-1 scale) for chain ranking
- **Thematic understanding** via OpenAI's CLIP model

## What it does

1. **Scans** all your videos in `https_/` directory (5,453 videos!)
2. **Analyzes** videos with AI:
   - Extracts keyframes at multiple points
   - Computes CLIP embeddings for semantic understanding
   - Detects scene boundaries
   - Analyzes color palettes and motion patterns
3. **Finds intelligent chains** where videos connect by:
   - Visual similarity (frame matching)
   - Content similarity (semantic themes)
   - Color harmony (smooth transitions)
   - Motion continuity (pacing)
4. **Ranks chains by quality** using multi-modal scoring
5. **Merges** chains into longer videos

## 🚀 Quick Start

### Option 1: Smart Mode (Recommended)

```bash
# Install all dependencies (includes PyTorch, CLIP, OpenCV)
pip install -r requirements.txt

# Test smart features on 10 videos
python video_analyzer_smart.py

# Start the smart server
python app.py
# Output: 🧠 Running in SMART mode with AI features

# Open your browser
open index.html
```

### Option 2: Basic Mode (Lightweight)

```bash
# Install minimal dependencies
pip install fastapi uvicorn pillow imagehash python-multipart aiofiles

# Start basic server
python app.py
# Output: 📊 Running in BASIC mode

# Open your browser
open index.html
```

The server will run on `http://localhost:8001`

## How to Use

### Basic Mode

1. **Click "🔍 Scan Videos"** - Analyzes all 5,453 videos
   - First run: ~3 hours (analyzing frames)
   - Results cached in `video_data.json`

2. **Adjust parameters:**
   - **Threshold**: Frame similarity (0-50, lower = stricter)
     - 10 = very similar frames
     - 20 = moderately similar
     - 30 = loosely similar
   - **Min Length**: Minimum videos per chain (2+)

3. **Click "⛓️ Find Chains"** - Discovers frame-matched chains

4. **Click "🔗 Merge Videos"** - Creates merged video

### Smart Mode 🧠 NEW!

1. **Click "🧠 Smart Scan"** - AI-powered analysis
   - First run: ~7.5 hours (full AI analysis)
   - Results cached in `video_data_smart.json`
   - **Tip**: Start with sample mode (100 videos) for testing

2. **Adjust quality threshold:**
   - **Min Score**: Chain quality (0-1)
     - 0.8+ = Excellent (seamless)
     - 0.6+ = Good (smooth)
     - 0.5+ = Acceptable
   - **Min Length**: Same as basic mode

3. **Click "🔗 Find Smart Chains"** - AI-powered chain discovery
   - Finds thematic connections
   - Ranks by quality score
   - Shows detailed scoring breakdown

4. **View quality scores:**
   - Frame similarity: Visual match
   - Semantic similarity: Content themes
   - Color continuity: Palette harmony
   - Motion continuity: Pacing match
   - **Final score**: Weighted combination

5. **Click "🔗 Merge Videos"** - Creates high-quality merged chain

## Project Structure

```
video-chains/
├── app.py                      # FastAPI server (smart mode support)
├── video_analyzer.py           # Basic frame analysis
├── video_analyzer_smart.py     # AI-powered analysis (NEW!)
├── index.html                  # Web interface
├── requirements.txt            # All dependencies
├── README.md                   # Original documentation
├── README_SMART.md            # This file
├── SMART_FEATURES.md          # Detailed smart mode guide
├── DATABASE_DESIGN.md         # Future enhancements
├── video_data.json            # Basic mode cache
├── video_data_smart.json      # Smart mode cache (NEW!)
├── video_matches.json         # Pre-computed frame matches
├── static/
│   └── theme.css              # Professional UI theme
└── merged/                    # Output directory
```

## Features

### Core Features (Both Modes)
- ✨ Clean, professional interface
- 💾 Intelligent caching (analyze once, use forever)
- 🎬 Hover video previews
- 🔗 One-click merging with ffmpeg
- 📊 Real-time statistics and progress

### Smart Mode Features 🧠
- 🤖 **Semantic understanding** via CLIP (OpenAI)
- 🎨 **Color harmony analysis** for smooth transitions
- 🏃 **Motion continuity** for pacing consistency
- 🎬 **Scene detection** for intelligent cuts
- 📈 **Quality scoring** ranks chains by coherence
- 🔬 **Multi-point frame analysis** (not just first/last)
- 🎯 **Thematic chains** based on content similarity
- ⚡ **GPU acceleration** support (10x faster with CUDA)

## Technical Details

### Basic Mode
- **Frame extraction**: ffmpeg
- **Perceptual hashing**: imagehash (16x16 average hash)
- **Chain discovery**: DFS on frame match graph
- **Video merging**: ffmpeg concat demuxer (lossless)

### Smart Mode 🧠
- **Deep learning framework**: PyTorch
- **Semantic model**: OpenAI CLIP ViT-B/32 (512D embeddings)
- **Scene detection**: PySceneDetect with content detector
- **Color analysis**: RGB histogram matching (32 bins)
- **Motion estimation**: Multi-frame hash difference
- **Scoring algorithm**: Weighted multi-modal fusion
  - Frame similarity: 40%
  - Semantic similarity: 30%
  - Color continuity: 15%
  - Motion continuity: 15%
- **Chain discovery**: Quality-aware DFS with A* characteristics
- **Caching**: JSON with numpy arrays for embeddings

## API Endpoints

### Core Endpoints
- `GET /api/info` - Get API status and feature availability
- `GET /api/progress` - Real-time scan progress
- `POST /api/merge` - Merge videos into single file
- `GET /api/video/{path}` - Serve video file
- `GET /api/merged/{filename}` - Serve merged video

### Basic Mode
- `POST /api/scan?force_refresh=false` - Analyze videos (basic)
- `GET /api/chains?threshold=15&min_length=2` - Find frame-matched chains

### Smart Mode 🧠
- `POST /api/scan?smart=true&sample_size=100` - AI-powered analysis
- `GET /api/chains/smart?min_score=0.6&min_length=2` - Find quality-ranked chains

**Full API documentation**: `http://localhost:8001/docs` (auto-generated by FastAPI)

## 📚 Documentation

- **[SMART_FEATURES.md](./SMART_FEATURES.md)** - Complete guide to AI features
- **[DATABASE_DESIGN.md](./DATABASE_DESIGN.md)** - Future PostgreSQL schema
- **API Docs**: `http://localhost:8001/docs` (interactive)

## Performance & Requirements

### Hardware Requirements

**Basic Mode:**
- CPU: 2+ cores
- RAM: 4GB
- Disk: 1GB free

**Smart Mode:**
- CPU: 4+ cores (8+ recommended)
- RAM: 8GB (16GB recommended)
- Disk: 5GB free (PyTorch models)
- GPU: Optional (10x faster with NVIDIA CUDA)

**Apple Silicon**: Excellent performance on M1/M2/M3 chips!

### Analysis Time

| Mode | Per Video | Total (5,453) | Cache File |
|------|-----------|---------------|------------|
| Basic | ~2s | ~3 hours | `video_data.json` |
| Smart | ~5s | ~7.5 hours | `video_data_smart.json` |

**Important**: Analysis is done once and cached forever!

## Roadmap

### ✅ Phase 1: Smart Chain Discovery (COMPLETED)
- Multi-modal scoring
- CLIP semantic similarity
- Scene detection
- Color & motion analysis

### 🚧 Phase 2: Character Recognition (Next)
- Face detection & tracking
- Character-based chains
- Screen time analysis

### 📅 Phase 3: Database Migration
- PostgreSQL with vector search
- Advanced querying
- Character embeddings

### 🌟 Phase 4: AI Enhancement
- Gemini Vision narration
- ElevenLabs voiceover
- Smooth transitions
- Background music

## Notes

- Videos stored in: `/Users/alialqattan/Downloads/8xSovia/https_/`
- Cache files: `video_data.json` (basic) and `video_data_smart.json` (smart)
- Merged videos: `merged/` directory
- All 5,453 videos can be analyzed!
- Smart mode is **backwards compatible** with basic mode

## Contributing

Found a bug or have an idea? Open an issue!

Want to improve the smart features? Check [SMART_FEATURES.md](./SMART_FEATURES.md) for technical details.

---

**Built with 🧠 intelligence and ❤️ quality**

*From basic frame matching to AI-powered narrative discovery*
