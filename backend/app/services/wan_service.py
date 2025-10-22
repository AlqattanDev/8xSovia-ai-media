"""Wan 2.1 Image-to-Video service - optimized for Apple Silicon M4 Pro"""
import os
import logging
from pathlib import Path
from typing import Optional
import torch
from PIL import Image
import asyncio

from ..config import get_settings

logger = logging.getLogger(__name__)

try:
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
    from diffusers.utils import export_to_video, load_image
    from transformers import CLIPVisionModel
    WAN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Wan dependencies not available: {e}. Image-to-video will be disabled.")
    WAN_AVAILABLE = False


class WanService:
    """Service for generating videos from images using Wan 2.1 (8GB VRAM optimized)"""

    def __init__(self, model_id: str = "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"):
        self.model_id = model_id
        self._pipe: Optional[WanImageToVideoPipeline] = None
        self._image_encoder: Optional[CLIPVisionModel] = None
        self._vae: Optional[AutoencoderKLWan] = None
        self._loading = False
        self._loaded = False

    @property
    def pipe(self) -> WanImageToVideoPipeline:
        """Lazy load the pipeline"""
        if self._pipe is None:
            self._load_pipeline()
        return self._pipe

    def _load_pipeline(self):
        """Load the Wan pipeline with Apple Silicon optimizations"""
        if self._loading or self._loaded or not WAN_AVAILABLE:
            return

        self._loading = True
        logger.info(f"Loading Wan 2.1 Image-to-Video model: {self.model_id}")

        # Set HF_TOKEN environment variable if available
        settings = get_settings()
        if settings.hf_token:
            os.environ["HF_TOKEN"] = settings.hf_token
            logger.info("HuggingFace token configured for authenticated model downloads")

        try:
            # Load image encoder with float32 (required for stability)
            logger.info("Loading CLIP image encoder...")
            self._image_encoder = CLIPVisionModel.from_pretrained(
                self.model_id,
                subfolder="image_encoder",
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )

            # Load VAE with float32
            logger.info("Loading VAE...")
            self._vae = AutoencoderKLWan.from_pretrained(
                self.model_id,
                subfolder="vae",
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )

            # Load main pipeline with bfloat16 for memory efficiency
            logger.info("Loading main pipeline...")
            self._pipe = WanImageToVideoPipeline.from_pretrained(
                self.model_id,
                vae=self._vae,
                image_encoder=self._image_encoder,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True
            )

            # Try MPS (Apple Silicon GPU) first, fall back to CPU if issues
            device_used = "cpu"
            if torch.backends.mps.is_available():
                try:
                    logger.info("Attempting to use MPS (Apple Silicon GPU)...")
                    self._pipe = self._pipe.to("mps")
                    device_used = "mps"
                    logger.info("Successfully enabled MPS acceleration")
                except Exception as mps_error:
                    logger.warning(f"MPS failed ({mps_error}), falling back to CPU")
                    # Fall back to CPU offload
                    logger.info("Enabling CPU offload for memory optimization...")
                    self._pipe.enable_sequential_cpu_offload()
            else:
                # No GPU available, use CPU offload
                logger.info("No GPU detected, enabling CPU offload for memory optimization...")
                self._pipe.enable_sequential_cpu_offload()

            # Enable memory-efficient attention
            self._pipe.enable_attention_slicing(slice_size=1)

            self._loaded = True
            logger.info("Wan 2.1 model loaded successfully (optimized for 8-12GB memory)")

        except Exception as e:
            logger.error(f"Failed to load Wan model: {e}")
            raise
        finally:
            self._loading = False

    async def generate_video(
        self,
        image_path: str,
        output_path: str,
        prompt: str = "",
        negative_prompt: str = "worst quality, inconsistent motion, blurry, jittery, distorted",
        num_frames: int = 49,
        fps: int = 16,
        guidance_scale: float = 5.0,
        height: int = 480,
        width: int = 832,
    ) -> str:
        """
        Generate video from image using Wan 2.1

        Args:
            image_path: Path to input image
            output_path: Path to save output video
            prompt: Optional text prompt to guide generation
            negative_prompt: Things to avoid in generation
            num_frames: Number of frames (49, 81, or 113 recommended)
            fps: Frames per second for output video
            guidance_scale: How closely to follow the prompt (1.0-10.0)
            height: Output height (480 recommended for 8GB)
            width: Output width (832 recommended for 16:9)

        Returns:
            Path to generated video file
        """
        logger.info(f"Generating video from {image_path} with Wan 2.1")

        # Run in thread pool to avoid blocking async event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_video_sync,
            image_path,
            output_path,
            prompt,
            negative_prompt,
            num_frames,
            fps,
            guidance_scale,
            height,
            width,
        )

    def _generate_video_sync(
        self,
        image_path: str,
        output_path: str,
        prompt: str,
        negative_prompt: str,
        num_frames: int,
        fps: int,
        guidance_scale: float,
        height: int,
        width: int,
    ) -> str:
        """Synchronous video generation"""
        try:
            # Load and prepare image
            logger.info(f"Loading image: {image_path}")
            image = Image.open(image_path).convert("RGB")

            # Resize image to target dimensions while maintaining aspect ratio
            img_width, img_height = image.size
            aspect = img_width / img_height
            target_aspect = width / height

            if aspect > target_aspect:
                # Image is wider - fit to width
                new_width = width
                new_height = int(width / aspect)
            else:
                # Image is taller - fit to height
                new_height = height
                new_width = int(height * aspect)

            # Ensure dimensions are divisible by 8
            new_width = (new_width // 8) * 8
            new_height = (new_height // 8) * 8

            logger.info(f"Resizing image from {img_width}x{img_height} to {new_width}x{new_height}")
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Generate video frames
            logger.info(f"Generating {num_frames} frames at {new_width}x{new_height} (this will take several minutes)...")

            output = self.pipe(
                image=image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                height=new_height,
                width=new_width,
                num_frames=num_frames,
                guidance_scale=guidance_scale,
            ).frames[0]

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Export to video
            logger.info(f"Exporting video to {output_path}")
            export_to_video(output, output_path, fps=fps)
            logger.info(f"Video generation complete: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise

    def unload(self):
        """Unload the model to free memory"""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
        if self._image_encoder is not None:
            del self._image_encoder
            self._image_encoder = None
        if self._vae is not None:
            del self._vae
            self._vae = None
        self._loaded = False

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Wan model unloaded")


# Global instance (lazy loaded)
_wan_service: Optional[WanService] = None


def get_wan_service() -> WanService:
    """Get or create the global Wan service instance"""
    global _wan_service
    if _wan_service is None:
        _wan_service = WanService()
    return _wan_service
