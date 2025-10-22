# 🧠 Smart Video Chain Finder - AI-Powered Features

## Overview

The Smart Video Chain Finder extends the basic frame-matching system with **AI-powered semantic understanding** and **multi-modal chain discovery**. Instead of just matching frames by visual similarity, the smart system understands **content, themes, colors, and motion patterns**.

---

## 🆚 Basic vs Smart Mode Comparison

| Feature | Basic Mode | Smart Mode |
|---------|-----------|------------|
| **Frame Analysis** | First & last frames only | Multi-point sampling (0%, 50%, 100%) |
| **Matching Algorithm** | Perceptual hash (imagehash) | Multi-modal scoring (4 signals) |
| **Semantic Understanding** | ❌ None | ✅ CLIP embeddings |
| **Scene Detection** | ❌ No | ✅ PySceneDetect |
| **Color Continuity** | ❌ No | ✅ Color histograms |
| **Motion Analysis** | ❌ No | ✅ Motion estimation |
| **Chain Quality Score** | Binary (match/no match) | 0-1 continuous score |
| **Dependencies** | Minimal (PIL, imagehash) | PyTorch, CLIP, OpenCV |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install all smart features
pip install -r requirements.txt

# This will install:
# - PyTorch (deep learning framework)
# - open-clip-torch (semantic similarity)
# - scenedetect (scene boundary detection)
# - opencv-python (video processing)
# - numpy, scikit-learn (numerical computing)
```

### 2. Test Smart Features (Sample Run)

```bash
# Test on 10 videos first
python video_analyzer_smart.py
```

This will:
- Analyze 10 sample videos with smart features
- Extract CLIP embeddings, color histograms, motion scores
- Find chains using multi-modal scoring
- Save results to `video_data_smart.json`

### 3. Start Smart API Server

```bash
python app.py
```

The server will auto-detect smart features and run in **SMART MODE** if dependencies are installed.

### 4. Use the API

```bash
# Check if smart mode is active
curl http://localhost:8001/api/info

# Smart scan (sample: first 100 videos)
curl -X POST "http://localhost:8001/api/scan?smart=true&sample_size=100"

# Find smart chains (min quality = 0.6)
curl "http://localhost:8001/api/chains/smart?min_score=0.6&min_length=2"
```

---

## 📊 Multi-Modal Chain Scoring

Smart mode combines **4 different signals** to compute chain quality:

### 1. Frame Similarity (40% weight)
- **What**: Perceptual hash distance between last frame of video1 and first frame of video2
- **How**: imagehash with 16x16 average hash
- **Range**: 0 (different) to 1 (identical)

### 2. Semantic Similarity (30% weight) 🧠 NEW
- **What**: CLIP embedding cosine similarity
- **How**: OpenAI's CLIP ViT-B/32 model
- **Range**: 0 (unrelated content) to 1 (same concept)
- **Example**: "sunset beach" → "ocean waves" = high score, "sunset beach" → "city night" = low score

### 3. Color Continuity (15% weight) 🎨 NEW
- **What**: Color histogram similarity
- **How**: RGB histogram matching with chi-square distance
- **Range**: 0 (different palettes) to 1 (same colors)
- **Use Case**: Smooth visual transitions (e.g., golden hour → golden hour)

### 4. Motion Continuity (15% weight) 🏃 NEW
- **What**: Action/motion level matching
- **How**: Frame-to-frame hash difference across video
- **Range**: 0 (motion mismatch) to 1 (same motion level)
- **Use Case**: Maintain pacing (action → action, calm → calm)

### Final Score Calculation

```
final_score = 0.40 × frame_similarity +
              0.30 × semantic_similarity +
              0.15 × color_continuity +
              0.15 × motion_continuity
```

**Interpretation:**
- `0.9 - 1.0`: Excellent chain (seamless transition)
- `0.7 - 0.9`: Good chain (smooth flow)
- `0.5 - 0.7`: Acceptable chain (minor discontinuity)
- `< 0.5`: Poor chain (jarring transition)

---

## 🔬 Technical Deep Dive

### CLIP Embeddings

**What is CLIP?**
- OpenAI's vision-language model
- Trained on 400M image-text pairs
- Understands semantic content of images

**How we use it:**
```python
# Extract embedding from video frame
image = extract_frame(video, timestamp=0)
embedding = clip_model.encode_image(image)  # 512-dimensional vector

# Compare two videos semantically
similarity = cosine_similarity(embedding1, embedding2)
```

**Benefits:**
- Matches videos with similar themes (e.g., "beach", "sunset", "ocean")
- Works even if frames look visually different
- Zero-shot (no training needed)

### Scene Detection

**What is PySceneDetect?**
- Automatic scene boundary detection
- Identifies cuts, fades, and content changes

**How we use it:**
```python
scenes = detect_scenes(video)
# Returns timestamps: [0.0, 5.2, 12.8, 18.3]
```

**Benefits:**
- Better understanding of video structure
- Future: Use scene boundaries for intelligent trimming
- Future: Only chain at scene transitions (avoid mid-scene cuts)

### Color Histograms

**How it works:**
```python
# Extract 32-bin RGB histogram
hist_r = histogram(pixels[:,:,0], bins=32)
hist_g = histogram(pixels[:,:,1], bins=32)
hist_b = histogram(pixels[:,:,2], bins=32)

# Compare using chi-square distance
similarity = 1 / (1 + chi_square(hist1, hist2))
```

**Benefits:**
- Ensures smooth color transitions
- Maintains visual aesthetic
- Works well for mood matching (warm tones → warm tones)

### Motion Estimation

**How it works:**
```python
# Extract frames at 25%, 50%, 75%
frame1 = extract_frame(video, duration * 0.25)
frame2 = extract_frame(video, duration * 0.50)
frame3 = extract_frame(video, duration * 0.75)

# Compute frame differences
diff = average_hash_distance(frame1, frame2, frame3)

# Higher diff = more motion
motion_score = min(1.0, diff / 32.0)
```

**Benefits:**
- Maintains pacing (high-action → high-action)
- Avoids jarring transitions (slow → fast)
- Improves viewer experience

---

## 🎯 Use Cases & Examples

### Use Case 1: Thematic Chains

**Goal**: Chain videos with similar themes (e.g., all beach scenes)

**Basic Mode**: Only matches if last frame of beach video looks like first frame of next beach video (rare!)

**Smart Mode**: CLIP understands "beach", "ocean", "waves" are related concepts. Finds thematic chains even with different camera angles.

**Result**: Longer, more coherent chains based on content.

### Use Case 2: Color-Graded Sequences

**Goal**: Create smooth visual flow with consistent color palette

**Basic Mode**: No color awareness, may chain golden hour → night scenes

**Smart Mode**: Color continuity score prioritizes videos with similar palettes

**Result**: Professional-looking sequences with visual harmony

### Use Case 3: Action Sequences

**Goal**: Build high-energy montages

**Basic Mode**: No motion awareness

**Smart Mode**: Motion continuity score groups high-action clips together

**Result**: Dynamic sequences that maintain viewer engagement

---

## 📈 Performance Considerations

### Analysis Speed

| Mode | Time per Video | Total (5,453 videos) |
|------|---------------|---------------------|
| Basic | ~2 seconds | ~3 hours |
| Smart | ~5 seconds | ~7.5 hours |

**First run is slow, but results are cached!**

### Hardware Requirements

**Minimum:**
- CPU: 4+ cores
- RAM: 8GB
- Disk: 5GB free (for PyTorch models)

**Recommended:**
- CPU: 8+ cores (or Apple Silicon M1/M2)
- RAM: 16GB
- GPU: NVIDIA with CUDA (10x faster CLIP inference)

**Apple Silicon Note**: Smart features work excellently on M1/M2/M3 chips using Metal acceleration.

### GPU Acceleration

```python
# Automatic GPU detection
if torch.cuda.is_available():
    clip_model = clip_model.cuda()
    print("✅ Using GPU")
else:
    print("⚠️  Using CPU (slower)")
```

To use GPU:
```bash
# Install PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## 🔧 Advanced Configuration

### Tuning Scoring Weights

Edit `video_analyzer_smart.py`:

```python
self.scoring_weights = {
    'frame_similarity': 0.40,      # Default
    'semantic_similarity': 0.30,   # Default
    'color_continuity': 0.15,      # Default
    'motion_continuity': 0.15      # Default
}
```

**For content-first chains** (theme over visuals):
```python
self.scoring_weights = {
    'frame_similarity': 0.20,
    'semantic_similarity': 0.60,  # Prioritize themes
    'color_continuity': 0.10,
    'motion_continuity': 0.10
}
```

**For visually smooth transitions**:
```python
self.scoring_weights = {
    'frame_similarity': 0.50,     # Prioritize visual match
    'semantic_similarity': 0.20,
    'color_continuity': 0.20,     # Prioritize color flow
    'motion_continuity': 0.10
}
```

### Adjusting Quality Threshold

```bash
# Strict: Only excellent chains (0.8+)
curl "http://localhost:8001/api/chains/smart?min_score=0.8"

# Relaxed: Accept more chains (0.5+)
curl "http://localhost:8001/api/chains/smart?min_score=0.5"
```

---

## 🧪 Testing & Validation

### Run Smart Analyzer Test

```bash
python video_analyzer_smart.py
```

**Expected output:**
```
🧪 Testing Smart Video Analyzer
============================================================

Loading CLIP model (ViT-B/32)...
✅ CLIP model loaded on CPU

📊 Analyzing sample of 10 videos...
🔍 Smart analyzing: generated_video.mp4
...
💾 Saving 10 videos to cache...
✅ Smart analysis complete! 10 videos processed

🔗 Finding smart chains...
✅ Found 5 smart chains

📈 RESULTS:
Total videos analyzed: 10
Chains found: 5

🏆 Top 3 Highest Quality Chains:
Chain #1:
  Length: 3 videos
  Avg Quality: 0.82
  Videos:
    1. video_001.mp4 (5.2s)
    2. video_042.mp4 (5.1s)
    3. video_089.mp4 (5.3s)
```

### Compare Basic vs Smart

```bash
# Basic chains
curl "http://localhost:8001/api/chains?min_length=3&threshold=15" > basic.json

# Smart chains
curl "http://localhost:8001/api/chains/smart?min_length=3&min_score=0.6" > smart.json

# Compare results
diff basic.json smart.json
```

**Expected difference**: Smart mode should find more thematically coherent chains, even if frame hashes don't match exactly.

---

## 📚 API Reference

### GET `/api/info`

Check smart mode status.

**Response:**
```json
{
  "message": "Smart Video Chain Finder API",
  "version": "2.0.0",
  "smart_mode": true,
  "videos": 5453,
  "features": {
    "frame_matching": true,
    "semantic_matching": true,
    "scene_detection": true,
    "multi_modal_scoring": true
  }
}
```

### POST `/api/scan`

Analyze videos with smart features.

**Parameters:**
- `force_refresh` (bool): Re-analyze even if cache exists
- `smart` (bool): Use smart analysis (default: true)
- `sample_size` (int, optional): Only analyze first N videos

**Example:**
```bash
# Smart scan of first 50 videos
curl -X POST "http://localhost:8001/api/scan?smart=true&sample_size=50"
```

### GET `/api/chains/smart`

Find chains using AI-powered matching.

**Parameters:**
- `min_score` (float): Minimum quality score (0-1, default: 0.6)
- `min_length` (int): Minimum chain length (default: 2)

**Response:**
```json
{
  "mode": "smart",
  "total_videos": 5453,
  "total_chains": 127,
  "chains": [
    {
      "length": 5,
      "avg_quality": 0.85,
      "total_duration": 26.3,
      "videos": [
        {
          "path": "video_001.mp4",
          "filename": "generated_video.mp4",
          "duration": 5.2,
          "transition_score": {
            "frame_similarity": 0.92,
            "semantic_similarity": 0.88,
            "color_continuity": 0.81,
            "motion_continuity": 0.76,
            "final_score": 0.86
          }
        }
      ]
    }
  ]
}
```

---

## 🛠️ Troubleshooting

### "Smart features not available"

**Cause**: Missing dependencies

**Fix**:
```bash
pip install -r requirements.txt
```

### "CLIP model failed to load"

**Cause**: PyTorch installation issue

**Fix**:
```bash
# Reinstall PyTorch
pip uninstall torch torchvision
pip install torch torchvision
```

### "Out of memory"

**Cause**: Not enough RAM for CLIP model

**Fix**:
```bash
# Analyze in smaller batches
curl -X POST "http://localhost:8001/api/scan?sample_size=10"
```

### Slow performance

**Solutions:**
1. Use GPU if available
2. Reduce sample size
3. Run analysis overnight
4. Use cached results (only analyze once!)

---

## 🚀 Future Enhancements (Roadmap)

### Phase 2: Character Recognition
- Face detection with InsightFace
- Character tracking across videos
- Character-based chains ("all videos with Character X")

### Phase 3: Database Migration
- PostgreSQL for advanced queries
- Vector search with pgvector
- Character embeddings database

### Phase 4: AI Generation
- Gemini Vision for narrative generation
- ElevenLabs TTS for voiceover
- Smooth transitions between clips
- Background music selection

---

## 📖 Learn More

- **CLIP Paper**: [Learning Transferable Visual Models](https://arxiv.org/abs/2103.00020)
- **PySceneDetect Docs**: [scenedetect.com](https://scenedetect.com)
- **Perceptual Hashing**: [jenssegers/imagehash](https://github.com/JohannesBuchner/imagehash)

---

**Built with 🧠 by the ultrathink team**

*No compromises. Only quality.*
