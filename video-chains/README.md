# 🔗 Video Chain Finder

A simple, clean tool to find and merge video chains by matching first and last frames.

## What it does

1. **Scans** all your videos in `https_/` directory (5,453 videos!)
2. **Extracts** first and last frames from each video
3. **Finds chains** where the last frame of one video matches the first frame of another
4. **Merges** chains into longer videos

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py

# Open your browser
open index.html
```

The server will run on `http://localhost:8001`

## How to Use

1. **Click "🔍 Scan Videos"** - This will analyze all 5,453 videos and extract frame hashes
   - First run will take ~1-2 hours (analyzing 5,453 videos)
   - Results are cached in `video_data.json` for instant future loads

2. **Adjust parameters:**
   - **Threshold**: How similar frames need to be (0-50, lower = stricter)
     - 10 = very similar frames
     - 20 = moderately similar
     - 30 = loosely similar
   - **Min Length**: Minimum number of videos in a chain (2+)

3. **Click "⛓️ Find Chains"** - Discovers all video chains

4. **Click "🔗 Merge Videos"** on any chain - Creates a single merged video

## Project Structure

```
video-chains/
├── app.py              # FastAPI server
├── video_analyzer.py   # Core analysis logic
├── index.html          # Web interface
├── requirements.txt    # Python dependencies
├── video_data.json     # Cached analysis results
└── merged/             # Output directory for merged videos
```

## Features

- ✨ Simple, clean interface
- 🚀 Fast frame-based matching using perceptual hashing
- 💾 Caches analysis results
- 🎬 Hover video previews
- 🔗 One-click merging with ffmpeg
- 📊 Real-time statistics

## Technical Details

- **Frame extraction**: ffmpeg
- **Perceptual hashing**: imagehash (16x16 average hash)
- **Chain discovery**: Depth-first search on frame match graph
- **Video merging**: ffmpeg concat demuxer (lossless)

## API Endpoints

- `POST /api/scan` - Analyze all videos
- `GET /api/chains?threshold=10&min_length=2` - Find chains
- `POST /api/merge` - Merge videos
- `GET /api/video/{path}` - Serve video
- `GET /api/merged/{filename}` - Serve merged video

## Notes

- Videos are stored in: `/Users/alialqattan/Downloads/8xSovia/https_/`
- First scan creates `video_data.json` cache
- Merged videos go to `merged/` directory
- All 5,453 videos will be analyzed!

---

Built from scratch for clean video chain discovery 🎬
