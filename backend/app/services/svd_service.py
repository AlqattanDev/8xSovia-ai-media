"""Stable Video Diffusion service for image-to-video generation"""
import os
import logging
from pathlib import Path
from typing import Optional, List
import torch
from PIL import Image
from diffusers import StableVideoDiffusionPipeline
import asyncio
from functools import lru_cache
import numpy as np

logger = logging.getLogger(__name__)


def export_frames_to_video(frames: List[Image.Image], output_path: str, fps: int = 7):
    """
    Export PIL Image frames to video file using imageio

    Args:
        frames: List of PIL Images
        output_path: Path to save video
        fps: Frames per second
    """
    try:
        import imageio
    except ImportError:
        raise ImportError("imageio is required for video export. Install with: pip install imageio imageio-ffmpeg")

    # Convert PIL Images to numpy arrays
    frame_arrays = [np.array(frame) for frame in frames]

    # Write video
    writer = imageio.get_writer(output_path, fps=fps, codec='libx264', pixelformat='yuv420p')
    for frame in frame_arrays:
        writer.append_data(frame)
    writer.close()


class SVDService:
    """Service for generating videos from images using Stable Video Diffusion"""

    def __init__(self, model_id: str = "stabilityai/stable-video-diffusion-img2vid"):
        # Using the base model (14 frames) instead of XT (25 frames) for lower memory usage
        self.model_id = model_id
        self._pipe: Optional[StableVideoDiffusionPipeline] = None
        self._loading = False
        self._loaded = False

    @property
    def pipe(self) -> StableVideoDiffusionPipeline:
        """Lazy load the pipeline"""
        if self._pipe is None:
            self._load_pipeline()
        return self._pipe

    def _load_pipeline(self):
        """Load the SVD pipeline with Apple Silicon optimizations"""
        if self._loading or self._loaded:
            return

        self._loading = True
        logger.info(f"Loading Stable Video Diffusion model: {self.model_id}")

        try:
            # Load with float32 initially
            self._pipe = StableVideoDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )

            # SVD requires too much memory for MPS, use CPU offload for memory efficiency
            # Sequential CPU offload loads each model component only when needed, minimizing memory usage
            logger.info("Using CPU offload for SVD (memory efficient)")
            self._pipe.enable_sequential_cpu_offload()

            # Enable memory-efficient attention with smallest chunk
            self._pipe.enable_attention_slicing(slice_size=1)

            self._loaded = True
            logger.info("SVD model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load SVD model: {e}")
            raise
        finally:
            self._loading = False

    async def generate_video(
        self,
        image_path: str,
        output_path: str,
        num_frames: int = 14,
        fps: int = 7,
        motion_bucket_id: int = 127,
        noise_aug_strength: float = 0.02,
        decode_chunk_size: int = 2,
    ) -> str:
        """
        Generate video from image using Stable Video Diffusion

        Args:
            image_path: Path to input image
            output_path: Path to save output video
            num_frames: Number of frames to generate (14 or 25)
            fps: Frames per second for output video
            motion_bucket_id: Motion intensity (0-255, higher = more motion)
            noise_aug_strength: Noise augmentation strength (0.0-1.0)
            decode_chunk_size: Decode frames in chunks to save memory

        Returns:
            Path to generated video file
        """
        logger.info(f"Generating video from {image_path}")

        # Run in thread pool to avoid blocking async event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_video_sync,
            image_path,
            output_path,
            num_frames,
            fps,
            motion_bucket_id,
            noise_aug_strength,
            decode_chunk_size,
        )

    def _generate_video_sync(
        self,
        image_path: str,
        output_path: str,
        num_frames: int,
        fps: int,
        motion_bucket_id: int,
        noise_aug_strength: float,
        decode_chunk_size: int,
    ) -> str:
        """Synchronous video generation"""
        try:
            logger.info(f"Starting video generation sync function")
            logger.info(f"Accessing pipe property, pipe is None: {self._pipe is None}")

            # Load and prepare image
            image = Image.open(image_path).convert("RGB")

            # Resize to optimal dimensions (SVD works best at 1024x576 or 576x1024)
            # Maintain aspect ratio and resize to fit
            width, height = image.size
            if width > height:
                # Landscape
                new_width = 1024
                new_height = int((height / width) * 1024)
                if new_height > 576:
                    new_height = 576
                    new_width = int((width / height) * 576)
            else:
                # Portrait
                new_height = 1024
                new_width = int((width / height) * 1024)
                if new_width > 576:
                    new_width = 576
                    new_height = int((height / width) * 576)

            # Ensure dimensions are divisible by 8 (required by SVD)
            new_width = (new_width // 8) * 8
            new_height = (new_height // 8) * 8

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image to {new_width}x{new_height}")

            # Generate video frames
            logger.info(f"Generating {num_frames} frames with motion_bucket_id={motion_bucket_id}")
            logger.info(f"About to call pipe, type: {type(self.pipe)}, is None: {self.pipe is None}")
            frames = self.pipe(
                image,
                num_frames=num_frames,
                decode_chunk_size=decode_chunk_size,
                motion_bucket_id=motion_bucket_id,
                noise_aug_strength=noise_aug_strength,
            ).frames[0]

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Export to video
            export_frames_to_video(frames, output_path, fps=fps)
            logger.info(f"Video saved to {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise

    def unload(self):
        """Unload the model to free memory"""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
            self._loaded = False
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            logger.info("SVD model unloaded")


# Global instance (lazy loaded)
_svd_service: Optional[SVDService] = None


def get_svd_service() -> SVDService:
    """Get or create the global SVD service instance"""
    global _svd_service
    if _svd_service is None:
        _svd_service = SVDService()
    return _svd_service
