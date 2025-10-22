#!/usr/bin/env python3
"""
Model Download Script for 8xSovia Video Generation

Downloads and sets up all required AI models:
- Wan 2.1 Image-to-Video (~28GB)
- Stable Video Diffusion (~12GB)
- RIFE v4.25 Frame Interpolation (~800MB)

Usage:
    python download_models.py [--wan] [--svd] [--rife] [--all]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelDownloader:
    """Handle downloading and setup of AI models"""

    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.models_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        self.rife_dir = self.backend_dir / "app" / "services" / "Practical-RIFE"

        # Model configurations
        self.models = {
            "wan": {
                "name": "Wan 2.1 Image-to-Video",
                "repo_id": "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
                "size_gb": 28,
                "type": "huggingface"
            },
            "svd": {
                "name": "Stable Video Diffusion",
                "repo_id": "stabilityai/stable-video-diffusion-img2vid",
                "size_gb": 12,
                "type": "huggingface"
            },
            "rife": {
                "name": "RIFE v4.25 Frame Interpolation",
                "repo_id": "AlexWortega/RIFE",
                "size_mb": 800,
                "type": "huggingface_rife"
            }
        }

        # Load HF token from environment
        self.hf_token = os.getenv("HF_TOKEN")
        if self.hf_token:
            logger.info("HuggingFace token found in environment")
        else:
            logger.warning("No HF_TOKEN found - some models may require authentication")

    def check_dependencies(self) -> bool:
        """Check if required packages are installed"""
        try:
            import torch
            import diffusers
            import transformers
            from huggingface_hub import hf_hub_download, snapshot_download
            logger.info("✓ All required packages installed")
            return True
        except ImportError as e:
            logger.error(f"✗ Missing required package: {e}")
            logger.error("Install with: pip install torch diffusers transformers huggingface_hub")
            return False

    def get_disk_space_gb(self) -> float:
        """Get available disk space in GB"""
        import shutil
        stat = shutil.disk_usage(self.backend_dir)
        return stat.free / (1024**3)

    def download_huggingface_model(self, repo_id: str, model_name: str, size_gb: int) -> bool:
        """Download a model from HuggingFace Hub"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading {model_name}")
        logger.info(f"Repository: {repo_id}")
        logger.info(f"Size: ~{size_gb}GB")
        logger.info(f"{'='*60}\n")

        # Check disk space
        available_gb = self.get_disk_space_gb()
        required_gb = size_gb + 5  # Add 5GB buffer

        if available_gb < required_gb:
            logger.error(f"✗ Insufficient disk space!")
            logger.error(f"  Available: {available_gb:.1f}GB")
            logger.error(f"  Required: {required_gb}GB")
            return False

        logger.info(f"Disk space check: {available_gb:.1f}GB available (need {required_gb}GB)")

        try:
            from huggingface_hub import snapshot_download

            logger.info("Starting download... (this may take 10-60 minutes)")
            logger.info("Files will be cached in: " + str(self.models_cache_dir))

            # Try without token first (for public models)
            try:
                logger.info("Attempting download without authentication (public model)...")
                cache_dir = snapshot_download(
                    repo_id=repo_id,
                    token=None,
                    resume_download=True,
                    local_files_only=False
                )
                logger.info(f"✓ {model_name} downloaded successfully!")
                logger.info(f"  Cached at: {cache_dir}")
                return True
            except Exception as e1:
                if "401" in str(e1) or "403" in str(e1):
                    # Try with token
                    if self.hf_token:
                        logger.info("Public access failed, trying with authentication token...")
                        cache_dir = snapshot_download(
                            repo_id=repo_id,
                            token=self.hf_token,
                            resume_download=True,
                            local_files_only=False
                        )
                        logger.info(f"✓ {model_name} downloaded successfully!")
                        logger.info(f"  Cached at: {cache_dir}")
                        return True
                    else:
                        raise e1
                else:
                    raise e1

        except Exception as e:
            logger.error(f"✗ Download failed: {e}")

            if "401" in str(e) or "403" in str(e):
                logger.error("\nAuthentication required!")
                logger.error("This model requires a HuggingFace account and token.")
                logger.error("\nSteps to fix:")
                logger.error("1. Create account at https://huggingface.co")
                logger.error("2. Generate token at https://huggingface.co/settings/tokens")
                logger.error("3. Set environment variable: export HF_TOKEN='your_token_here'")
                logger.error("4. Re-run this script")

            return False

    def download_rife_model(self) -> bool:
        """Download and setup RIFE model"""
        logger.info(f"\n{'='*60}")
        logger.info("Downloading RIFE v4.25 Frame Interpolation")
        logger.info(f"{'='*60}\n")

        try:
            import shutil
            import urllib.request

            # Create RIFE directory structure
            train_log_dir = self.rife_dir / "train_log"
            train_log_dir.mkdir(parents=True, exist_ok=True)

            dest_path = train_log_dir / "flownet.pkl"

            # Try multiple download sources
            sources = [
                {
                    "name": "HuggingFace (public)",
                    "method": "huggingface",
                    "repo": "AlexWortega/RIFE",
                    "file": "flownet.pkl"
                },
                {
                    "name": "Direct download (GitHub LFS)",
                    "method": "direct",
                    "url": "https://github.com/hzwer/Practical-RIFE/releases/download/v4.25/flownet_v4.25.pkl"
                }
            ]

            for source in sources:
                try:
                    logger.info(f"Trying {source['name']}...")

                    if source['method'] == 'huggingface':
                        from huggingface_hub import hf_hub_download

                        # Try without token first
                        try:
                            model_file = hf_hub_download(
                                repo_id=source['repo'],
                                filename=source['file'],
                                token=None,
                                resume_download=True
                            )
                        except Exception as e1:
                            # Try with token if available
                            if self.hf_token and ("401" in str(e1) or "403" in str(e1)):
                                logger.info("  Trying with authentication token...")
                                model_file = hf_hub_download(
                                    repo_id=source['repo'],
                                    filename=source['file'],
                                    token=self.hf_token,
                                    resume_download=True
                                )
                            else:
                                raise e1

                        shutil.copy(model_file, dest_path)

                    elif source['method'] == 'direct':
                        logger.info(f"  Downloading from: {source['url']}")
                        urllib.request.urlretrieve(source['url'], dest_path)

                    # Verify download
                    if dest_path.exists() and dest_path.stat().st_size > 1000000:  # >1MB
                        logger.info(f"✓ RIFE model installed to: {train_log_dir}")
                        logger.info(f"✓ RIFE model verified ({dest_path.stat().st_size / 1024**2:.1f}MB)")
                        return True
                    else:
                        logger.warning(f"✗ Downloaded file appears incomplete, trying next source...")
                        if dest_path.exists():
                            dest_path.unlink()

                except Exception as e:
                    logger.warning(f"  Failed: {e}")
                    logger.info("  Trying next source...")
                    continue

            # All sources failed
            logger.error("✗ All download sources failed")
            logger.info("\nAlternative: Manual installation")
            logger.info("1. Download from: https://github.com/hzwer/Practical-RIFE/releases")
            logger.info("2. Look for: flownet_v4.25.pkl or similar")
            logger.info("3. Save as: " + str(train_log_dir / "flownet.pkl"))
            return False

        except Exception as e:
            logger.error(f"✗ RIFE download failed: {e}")
            logger.info("\nAlternative: Manual installation")
            logger.info("1. Download from: https://github.com/hzwer/Practical-RIFE/releases")
            logger.info("2. Extract to: " + str(self.rife_dir / "train_log"))
            return False

    def verify_model_installation(self, model_key: str) -> bool:
        """Verify a model is properly installed"""
        logger.info(f"\nVerifying {model_key.upper()} installation...")

        if model_key == "rife":
            # Check for RIFE files
            flownet_path = self.rife_dir / "train_log" / "flownet.pkl"
            if flownet_path.exists():
                logger.info(f"✓ RIFE model found: {flownet_path}")
                return True
            else:
                logger.warning(f"✗ RIFE model not found at: {flownet_path}")
                return False

        # For HuggingFace models, try to load them
        try:
            import torch
            from diffusers import AutoencoderKL

            repo_id = self.models[model_key]["repo_id"]

            logger.info(f"Attempting to load {repo_id}...")

            # Try loading a small component to verify download
            if model_key == "wan":
                from diffusers import WanImageToVideoPipeline
                # Just verify the model exists in cache
                logger.info("Checking HuggingFace cache...")
                cache_path = self.models_cache_dir / f"models--{repo_id.replace('/', '--')}"
                if cache_path.exists():
                    logger.info(f"✓ {model_key.upper()} found in cache")
                    return True
                else:
                    logger.warning(f"✗ {model_key.upper()} not found in cache")
                    return False

            elif model_key == "svd":
                from diffusers import StableVideoDiffusionPipeline
                cache_path = self.models_cache_dir / f"models--{repo_id.replace('/', '--')}"
                if cache_path.exists():
                    logger.info(f"✓ {model_key.upper()} found in cache")
                    return True
                else:
                    logger.warning(f"✗ {model_key.upper()} not found in cache")
                    return False

        except Exception as e:
            logger.warning(f"Verification check failed: {e}")
            return False

    def download_model(self, model_key: str) -> bool:
        """Download a specific model"""
        if model_key not in self.models:
            logger.error(f"Unknown model: {model_key}")
            return False

        model_config = self.models[model_key]

        # Check if already installed
        if self.verify_model_installation(model_key):
            logger.info(f"✓ {model_config['name']} already installed - skipping download")
            return True

        # Download based on type
        if model_config["type"] == "huggingface":
            return self.download_huggingface_model(
                model_config["repo_id"],
                model_config["name"],
                model_config["size_gb"]
            )
        elif model_config["type"] == "huggingface_rife":
            return self.download_rife_model()

        return False

    def show_summary(self):
        """Show summary of installed models"""
        logger.info("\n" + "="*60)
        logger.info("MODEL INSTALLATION SUMMARY")
        logger.info("="*60)

        for model_key, config in self.models.items():
            installed = self.verify_model_installation(model_key)
            status = "✓ INSTALLED" if installed else "✗ NOT INSTALLED"
            logger.info(f"\n{config['name']}:")
            logger.info(f"  Status: {status}")
            logger.info(f"  Size: {config.get('size_gb', config.get('size_mb', 0) / 1000)}GB")

        logger.info("\n" + "="*60)
        logger.info("\nNext steps:")
        logger.info("1. Start the backend server:")
        logger.info("   cd backend && python -m uvicorn app.main:app --reload")
        logger.info("\n2. Check model status at:")
        logger.info("   http://localhost:8000/api/models/status")
        logger.info("\n3. Open the frontend and test video generation!")
        logger.info("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download AI models for 8xSovia video generation"
    )
    parser.add_argument(
        "--wan",
        action="store_true",
        help="Download Wan 2.1 model (~28GB)"
    )
    parser.add_argument(
        "--svd",
        action="store_true",
        help="Download Stable Video Diffusion model (~12GB)"
    )
    parser.add_argument(
        "--rife",
        action="store_true",
        help="Download RIFE frame interpolation model (~800MB)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all models (requires ~40GB free space)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify installations, don't download"
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = ModelDownloader()

    # Check dependencies
    if not downloader.check_dependencies():
        logger.error("\nPlease install required packages first:")
        logger.error("pip install torch diffusers transformers huggingface_hub")
        return 1

    # If verify only
    if args.verify:
        downloader.show_summary()
        return 0

    # Determine which models to download
    models_to_download = []
    if args.all:
        models_to_download = ["wan", "svd", "rife"]
    else:
        if args.wan:
            models_to_download.append("wan")
        if args.svd:
            models_to_download.append("svd")
        if args.rife:
            models_to_download.append("rife")

    # If no models specified, show help
    if not models_to_download:
        parser.print_help()
        logger.info("\n" + "="*60)
        logger.info("RECOMMENDED: Download all models for best experience")
        logger.info("="*60)
        logger.info("\nQuick start:")
        logger.info("  python download_models.py --all")
        logger.info("\nOr download individually:")
        logger.info("  python download_models.py --wan    # Image-to-video (28GB)")
        logger.info("  python download_models.py --svd    # Faster alternative (12GB)")
        logger.info("  python download_models.py --rife   # Smooth transitions (800MB)")
        logger.info("\nVerify installation:")
        logger.info("  python download_models.py --verify")
        return 0

    # Show download plan
    total_size = sum(
        downloader.models[m].get("size_gb", downloader.models[m].get("size_mb", 0) / 1000)
        for m in models_to_download
    )
    available_space = downloader.get_disk_space_gb()

    logger.info("\n" + "="*60)
    logger.info("DOWNLOAD PLAN")
    logger.info("="*60)
    logger.info(f"\nModels to download: {', '.join(m.upper() for m in models_to_download)}")
    logger.info(f"Total size: ~{total_size:.1f}GB")
    logger.info(f"Available space: {available_space:.1f}GB")
    logger.info(f"Estimated time: {total_size * 2:.0f}-{total_size * 5:.0f} minutes")
    logger.info("\n" + "="*60)

    # Confirm
    try:
        response = input("\nProceed with download? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            logger.info("Download cancelled")
            return 0
    except KeyboardInterrupt:
        logger.info("\nDownload cancelled")
        return 0

    # Download models
    success_count = 0
    for model_key in models_to_download:
        if downloader.download_model(model_key):
            success_count += 1
        else:
            logger.warning(f"Failed to download {model_key} - continuing with remaining models")

    # Show summary
    logger.info(f"\n✓ Successfully downloaded {success_count}/{len(models_to_download)} models")
    downloader.show_summary()

    return 0 if success_count == len(models_to_download) else 1


if __name__ == "__main__":
    sys.exit(main())
