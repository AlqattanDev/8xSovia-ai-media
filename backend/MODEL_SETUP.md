# AI Model Setup Guide

This guide covers downloading and setting up all AI models required for 8xSovia's video generation features.

## Quick Start

Download all models with a single command:

```bash
cd backend
python download_models.py --all
```

This will download:
- **Wan 2.1** (~28GB) - High-quality image-to-video generation
- **SVD** (~12GB) - Faster alternative for image-to-video
- **RIFE** (~800MB) - Smooth video transitions

**Total**: ~40GB | **Time**: 20-120 minutes depending on internet speed

## Prerequisites

### 1. Install Required Packages

```bash
pip install torch diffusers transformers huggingface_hub
```

### 2. HuggingFace Authentication (Optional but Recommended)

Some models may require authentication:

1. Create account at https://huggingface.co
2. Generate token at https://huggingface.co/settings/tokens
3. Set environment variable:

```bash
export HF_TOKEN='your_token_here'
```

Or add to your `.env` file:

```bash
HF_TOKEN=your_token_here
```

### 3. Check Disk Space

Ensure you have at least **45GB** of free disk space:

```bash
df -h /Users/alialqattan/Downloads/8xSovia
```

## Individual Model Downloads

### Option 1: Wan 2.1 Only (~28GB)

Best quality, slower generation (3-5 minutes per video)

```bash
python download_models.py --wan
```

**Specifications:**
- Model: Wan2.1-I2V-14B-480P
- Size: ~28GB
- Output: 49-113 frames (3-7 seconds)
- Resolution: 480P (832x480)
- Best for: High-quality production videos

### Option 2: SVD Only (~12GB)

Faster generation (1-2 minutes per video)

```bash
python download_models.py --svd
```

**Specifications:**
- Model: Stable Video Diffusion (stabilityai)
- Size: ~12GB
- Output: 14-25 frames (~2 seconds)
- Resolution: 1024x576 or 576x1024
- Best for: Quick previews, testing

### Option 3: RIFE Only (~800MB)

AI-powered smooth video transitions

```bash
python download_models.py --rife
```

**Specifications:**
- Model: RIFE v4.25 Frame Interpolation
- Size: ~800MB
- Purpose: Smooth transitions when merging videos
- Optional: Falls back to FFmpeg simple concat if not installed

## Verification

Check installation status:

```bash
python download_models.py --verify
```

Or via API (with backend running):

```bash
curl http://localhost:8000/api/models/status
```

Expected output:

```json
{
  "wan": {
    "name": "Wan 2.1 Image-to-Video",
    "available": true,
    "installed": true,
    "size_gb": 28
  },
  "svd": {
    "name": "Stable Video Diffusion",
    "available": true,
    "installed": true,
    "size_gb": 12
  },
  "rife": {
    "name": "RIFE Frame Interpolation",
    "available": true,
    "installed": true,
    "size_mb": 800
  },
  "gpu": {
    "mps_available": true,
    "device": "mps"
  }
}
```

## Storage Locations

Models are cached in HuggingFace's default cache directory:

**macOS/Linux:**
```
~/.cache/huggingface/hub/
```

**Windows:**
```
C:\Users\<username>\.cache\huggingface\hub\
```

**RIFE specific location:**
```
backend/app/services/Practical-RIFE/train_log/flownet.pkl
```

## GPU Acceleration (Apple Silicon)

The application automatically uses MPS (Metal Performance Shaders) on M-series Macs:

- **M4 Pro**: ~8GB VRAM recommended for Wan 2.1
- **M3/M3 Pro**: Works with CPU offload
- **M1/M2**: Slower but functional

Check GPU usage during generation:

```bash
# In a separate terminal
sudo powermetrics --samplers gpu_power -i1000 -n1
```

## Troubleshooting

### Download Failed

1. **Check internet connection**
2. **Verify disk space**: `df -h`
3. **Check HF token**: `echo $HF_TOKEN`
4. **Retry with resume**: The script automatically resumes interrupted downloads

### Authentication Error (401/403)

```
This model requires a HuggingFace account and token.
```

**Solution:**
1. Create account at https://huggingface.co
2. Generate token at https://huggingface.co/settings/tokens
3. Set `HF_TOKEN` environment variable
4. Re-run download script

### Insufficient Disk Space

```
Insufficient disk space! Available: 20.0GB Required: 45GB
```

**Solutions:**
- Free up space
- Download models individually (--wan, --svd, or --rife)
- Use external drive and symlink cache directory

### RIFE Model Not Found

If RIFE download fails, manually install:

1. Download from: https://github.com/hzwer/Practical-RIFE/releases
2. Extract `flownet.pkl` to:
   ```
   backend/app/services/Practical-RIFE/train_log/flownet.pkl
   ```

### Model Loading Slow

First-time model loading can take 1-3 minutes as models are loaded into memory.

**Normal behavior:**
- Wan 2.1: ~2-3 minutes first load
- SVD: ~1-2 minutes first load
- RIFE: ~10-20 seconds first load

## Performance Benchmarks

Based on M4 Pro (24GB RAM):

| Model | First Load | Generation Time | GPU Usage | Quality |
|-------|-----------|----------------|-----------|---------|
| Wan 2.1 | 2-3 min | 3-5 min/video | 60-80% | Excellent |
| SVD | 1-2 min | 1-2 min/video | 40-60% | Good |
| RIFE | 10-20 sec | ~2 sec/transition | 20-40% | N/A |

## Recommended Setup

**For best experience**, download all three models:

```bash
python download_models.py --all
```

This gives you:
- **Flexibility**: Choose Wan for quality or SVD for speed
- **Smooth transitions**: RIFE interpolation when merging videos
- **Offline capability**: No downloads during generation

**Minimum setup** (just to get started):

```bash
python download_models.py --svd --rife
```

This uses only 13GB and provides fast generation + smooth merging.

## Next Steps

After downloading models:

1. **Start the backend**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Check model status**:
   ```bash
   curl http://localhost:8000/api/models/status
   ```

3. **Open frontend**:
   ```
   Open index.html in browser
   ```

4. **Test generation**:
   - Click any image in gallery
   - Click "🎬 Generate Video" button
   - Select model (Wan or SVD)
   - Wait for generation to complete

## Uninstalling Models

To free up disk space:

```bash
# Remove HuggingFace cache
rm -rf ~/.cache/huggingface/hub/models--Wan-AI--Wan2.1-I2V-14B-480P-Diffusers
rm -rf ~/.cache/huggingface/hub/models--stabilityai--stable-video-diffusion-img2vid

# Remove RIFE model
rm -rf backend/app/services/Practical-RIFE/train_log/
```

## Support

For issues with:
- **Model downloads**: Check HuggingFace status page
- **GPU acceleration**: Verify PyTorch MPS support
- **Generation errors**: Check backend logs at `backend/app.log`

## Advanced Configuration

### Custom Model Paths

To use a custom cache directory:

```bash
export HF_HOME=/path/to/custom/cache
python download_models.py --all
```

### Offline Mode

After downloading, you can work offline by setting:

```bash
export HF_HUB_OFFLINE=1
```

### Model Variants

The script downloads optimized versions:
- Wan: `Wan2.1-I2V-14B-480P-Diffusers` (bfloat16)
- SVD: `stable-video-diffusion-img2vid` (float32 with offload)
- RIFE: v4.25 (latest stable)

To use different variants, modify `download_models.py` configuration.
