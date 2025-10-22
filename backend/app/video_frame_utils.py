"""Video frame extraction and perceptual hashing utilities"""
import subprocess
import tempfile
import os
from pathlib import Path
from PIL import Image
import imagehash
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def extract_frame(video_path: str, frame_position: str = "0") -> Optional[Image.Image]:
    """
    Extract a single frame from a video using ffmpeg

    Args:
        video_path: Path to the video file
        frame_position: Time position (e.g., "0" for first frame, "00:00:05" for 5 seconds in)

    Returns:
        PIL Image object or None if extraction fails
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        # Extract frame using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', frame_position,
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            tmp_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )

        if result.returncode == 0 and os.path.exists(tmp_path):
            image = Image.open(tmp_path)
            image.load()  # Load image data before temp file is deleted
            os.unlink(tmp_path)
            return image
        else:
            logger.error(f"ffmpeg failed: {result.stderr.decode()}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return None

    except Exception as e:
        logger.error(f"Error extracting frame from {video_path}: {str(e)}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Get video duration in seconds using ffprobe

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds or None if failed
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )

        if result.returncode == 0:
            duration = float(result.stdout.decode().strip())
            return duration
        return None

    except Exception as e:
        logger.error(f"Error getting video duration for {video_path}: {str(e)}")
        return None


def compute_perceptual_hash(image: Image.Image, hash_size: int = 16) -> str:
    """
    Compute perceptual hash of an image

    Args:
        image: PIL Image object
        hash_size: Size of the hash (default 16 for 256-bit hash)

    Returns:
        Hex string representation of the hash
    """
    # Use average hash (aHash) - good balance of speed and accuracy
    phash = imagehash.average_hash(image, hash_size=hash_size)
    return str(phash)


def extract_first_and_last_frame_hashes(video_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract first and last frames from a video and compute their perceptual hashes

    Args:
        video_path: Path to the video file

    Returns:
        Tuple of (first_frame_hash, last_frame_hash) or (None, None) if extraction fails
    """
    # Check if file exists
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None, None

    # Extract first frame
    first_frame = extract_frame(video_path, "0")
    if first_frame is None:
        logger.warning(f"Could not extract first frame from {video_path}")
        return None, None

    first_hash = compute_perceptual_hash(first_frame)

    # Get video duration to extract last frame
    duration = get_video_duration(video_path)
    if duration is None:
        logger.warning(f"Could not get duration for {video_path}")
        return first_hash, None

    # Extract last frame (0.1 seconds before end to avoid black frames)
    last_frame_time = max(0, duration - 0.1)
    last_frame = extract_frame(video_path, str(last_frame_time))

    if last_frame is None:
        logger.warning(f"Could not extract last frame from {video_path}")
        return first_hash, None

    last_hash = compute_perceptual_hash(last_frame)

    return first_hash, last_hash


def hash_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two perceptual hashes

    Args:
        hash1: First hash string
        hash2: Second hash string

    Returns:
        Hamming distance (number of differing bits)
    """
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception as e:
        logger.error(f"Error calculating hash distance: {str(e)}")
        return 999  # Return large distance on error


def frames_match(hash1: str, hash2: str, threshold: int = 10) -> bool:
    """
    Check if two frame hashes are similar enough to be considered a match

    Args:
        hash1: First hash string
        hash2: Second hash string
        threshold: Maximum Hamming distance for a match (default 10)

    Returns:
        True if frames match, False otherwise
    """
    distance = hash_distance(hash1, hash2)
    return distance <= threshold
