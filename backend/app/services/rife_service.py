"""RIFE video frame interpolation service for smooth transitions"""
import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
import torch
import numpy as np
import cv2
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageSequenceClip
except ImportError:
    # MoviePy 2.x has different imports
    from moviepy import VideoFileClip, concatenate_videoclips, ImageSequenceClip
import asyncio

logger = logging.getLogger(__name__)

# Add Practical-RIFE to path
RIFE_PATH = Path(__file__).parent / "Practical-RIFE"
sys.path.insert(0, str(RIFE_PATH))

try:
    from model.pytorch_msssim import ssim_matlab
    from train_log.RIFE_HDv3 import Model
except ImportError as e:
    logger.warning(f"RIFE model import failed: {e}. RIFE features will be disabled.")
    Model = None


class RIFEService:
    """Service for video frame interpolation and smooth merging using RIFE"""

    def __init__(self):
        self.model: Optional[Model] = None
        self.device = None
        self._loaded = False

    def _load_model(self):
        """Load RIFE model (lazy loading)"""
        if self._loaded or Model is None:
            return

        logger.info("Loading RIFE model...")

        # Determine device - try GPU first, fall back to CPU
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            logger.info("Using CUDA for RIFE")
        elif torch.backends.mps.is_available():
            try:
                # Try MPS first
                self.device = torch.device("mps")
                logger.info("Attempting to use MPS (Apple Silicon GPU) for RIFE")
            except Exception as e:
                logger.warning(f"MPS initialization failed: {e}, falling back to CPU")
                self.device = torch.device("cpu")
        else:
            self.device = torch.device("cpu")
            logger.info("Using CPU for RIFE")

        try:
            self.model = Model()
            self.model.load_model(str(RIFE_PATH / "train_log"), -1)
            self.model.eval()
            self.model.device()
            self._loaded = True
            logger.info("RIFE model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load RIFE model: {e}")
            self.model = None

    def _interpolate_frames(self, frame1: np.ndarray, frame2: np.ndarray, num_frames: int = 5) -> List[np.ndarray]:
        """
        Interpolate frames between two frames using RIFE

        Args:
            frame1: First frame (numpy array, RGB)
            frame2: Second frame (numpy array, RGB)
            num_frames: Number of intermediate frames to generate

        Returns:
            List of interpolated frames (including original frames)
        """
        if self.model is None:
            logger.warning("RIFE model not loaded, returning original frames")
            return [frame1, frame2]

        try:
            # Convert frames to torch tensors
            img0 = torch.from_numpy(frame1.transpose(2, 0, 1)).float().unsqueeze(0) / 255.0
            img1 = torch.from_numpy(frame2.transpose(2, 0, 1)).float().unsqueeze(0) / 255.0

            if self.device.type != "cpu":
                img0 = img0.to(self.device)
                img1 = img1.to(self.device)

            interpolated = [frame1]

            # Generate intermediate frames
            for i in range(1, num_frames + 1):
                timestep = i / (num_frames + 1)

                with torch.no_grad():
                    middle = self.model.inference(img0, img1, timestep)

                # Convert back to numpy
                frame = (middle[0].cpu().numpy().transpose(1, 2, 0) * 255.0).astype(np.uint8)
                interpolated.append(frame)

            interpolated.append(frame2)
            return interpolated

        except Exception as e:
            logger.error(f"Frame interpolation failed: {e}")
            return [frame1, frame2]

    async def merge_videos_with_transitions(
        self,
        video_paths: List[str],
        output_path: str,
        transition_frames: int = 10,
        fps: int = 30
    ) -> str:
        """
        Merge multiple videos with smooth RIFE transitions

        Args:
            video_paths: List of paths to video files to merge
            output_path: Path to save merged video
            transition_frames: Number of interpolated frames for each transition
            fps: Frames per second for output video

        Returns:
            Path to merged video
        """
        logger.info(f"Merging {len(video_paths)} videos with RIFE transitions")

        # Load model if not loaded
        self._load_model()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._merge_videos_sync,
            video_paths,
            output_path,
            transition_frames,
            fps
        )

    def _merge_videos_sync(
        self,
        video_paths: List[str],
        output_path: str,
        transition_frames: int,
        fps: int
    ) -> str:
        """Synchronous video merging with transitions"""
        try:
            clips = []

            for i, video_path in enumerate(video_paths):
                logger.info(f"Processing video {i+1}/{len(video_paths)}: {video_path}")

                # Load video
                clip = VideoFileClip(video_path)

                # Add main clip
                clips.append(clip)

                # Add transition to next video (except for last video)
                if i < len(video_paths) - 1 and transition_frames > 0 and self.model is not None:
                    logger.info(f"Generating transition {i+1}/{len(video_paths)-1}")

                    # Get last frame of current video
                    last_frame = clip.get_frame(clip.duration)

                    # Get first frame of next video
                    next_clip = VideoFileClip(video_paths[i + 1])
                    first_frame = next_clip.get_frame(0)
                    next_clip.close()

                    # Resize frames to match if needed
                    if last_frame.shape != first_frame.shape:
                        first_frame = cv2.resize(first_frame, (last_frame.shape[1], last_frame.shape[0]))

                    # Generate interpolated frames
                    transition_frames_list = self._interpolate_frames(
                        last_frame,
                        first_frame,
                        num_frames=transition_frames
                    )

                    # Create transition clip (exclude first and last frames to avoid duplication)
                    if len(transition_frames_list) > 2:
                        transition_clip = ImageSequenceClip(
                            transition_frames_list[1:-1],
                            fps=fps
                        )
                        clips.append(transition_clip)

            # Concatenate all clips
            logger.info("Concatenating clips...")
            final_clip = concatenate_videoclips(clips, method="compose")

            # Write output
            logger.info(f"Writing output to {output_path}")
            final_clip.write_videofile(
                output_path,
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}.temp-audio.m4a",
                remove_temp=True,
                logger=None  # Suppress moviepy progress
            )

            # Clean up
            for clip in clips:
                clip.close()
            final_clip.close()

            logger.info(f"Video merging complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Video merging failed: {e}")
            raise

    async def simple_concatenate(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """
        Simple video concatenation without transitions (fast, uses FFmpeg)

        Args:
            video_paths: List of paths to video files
            output_path: Path to save merged video

        Returns:
            Path to merged video
        """
        logger.info(f"Simple concatenation of {len(video_paths)} videos")

        # Create concat file for FFmpeg
        concat_file = output_path + ".concat.txt"

        try:
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")

            # Run FFmpeg concat
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',  # Overwrite output
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")

            logger.info(f"Simple concatenation complete: {output_path}")
            return output_path

        finally:
            # Clean up concat file
            if os.path.exists(concat_file):
                os.remove(concat_file)


# Global instance
_rife_service: Optional[RIFEService] = None


def get_rife_service() -> RIFEService:
    """Get or create the global RIFE service instance"""
    global _rife_service
    if _rife_service is None:
        _rife_service = RIFEService()
    return _rife_service
