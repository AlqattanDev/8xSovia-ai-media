"""
Video Chain Analyzer - Scan, extract frames, and find video chains
"""
import os
import subprocess
import tempfile
import json
import hashlib
from pathlib import Path
from PIL import Image
import imagehash
from typing import Dict, List, Tuple, Optional


class VideoAnalyzer:
    def __init__(self, video_dir: str, cache_file: str = "video_data.json", match_cache_file: str = "video_matches.json"):
        self.video_dir = video_dir
        self.cache_file = cache_file
        self.match_cache_file = match_cache_file
        self.videos: Dict[str, dict] = {}
        self.match_graph: Dict[str, List[str]] = {}  # Pre-computed matches
        self.scan_progress = {
            "total": 0,
            "processed": 0,
            "status": "idle",
            "message": ""
        }

    def scan_videos(self) -> List[str]:
        """Scan directory for all MP4 videos"""
        print(f"Scanning {self.video_dir} for videos...")
        video_files = []
        for root, dirs, files in os.walk(self.video_dir):
            for file in files:
                if file.endswith('.mp4'):
                    video_files.append(os.path.join(root, file))
        print(f"Found {len(video_files)} videos")
        return video_files

    def extract_frame(self, video_path: str, frame_position: str = "0") -> Optional[Image.Image]:
        """Extract a single frame from video using ffmpeg"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_path = tmp_file.name

            cmd = [
                'ffmpeg', '-ss', frame_position, '-i', video_path,
                '-vframes', '1', '-q:v', '2', '-y', tmp_path
            ]

            result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=10)

            if result.returncode == 0 and os.path.exists(tmp_path):
                image = Image.open(tmp_path)
                image.load()
                os.unlink(tmp_path)
                return image
            else:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                return None
        except Exception as e:
            print(f"Error extracting frame from {video_path}: {e}")
            return None

    def get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds"""
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.decode().strip())
            return None
        except Exception as e:
            print(f"Error getting duration for {video_path}: {e}")
            return None

    def compute_hash(self, image: Image.Image) -> str:
        """Compute perceptual hash of image"""
        return str(imagehash.average_hash(image, hash_size=16))

    def analyze_video(self, video_path: str) -> Optional[dict]:
        """Extract first and last frame hashes from video"""
        print(f"Analyzing: {os.path.basename(video_path)}")

        # Extract first frame
        first_frame = self.extract_frame(video_path, "0")
        if not first_frame:
            return None

        first_hash = self.compute_hash(first_frame)

        # Get duration and extract last frame
        duration = self.get_video_duration(video_path)
        if not duration:
            return None

        last_frame_time = max(0, duration - 0.1)
        last_frame = self.extract_frame(video_path, str(last_frame_time))
        if not last_frame:
            return None

        last_hash = self.compute_hash(last_frame)

        # Get file info
        file_size = os.path.getsize(video_path)

        return {
            "path": video_path,
            "filename": os.path.basename(video_path),
            "first_hash": first_hash,
            "last_hash": last_hash,
            "duration": duration,
            "size": file_size
        }

    def analyze_all(self, force_refresh: bool = False):
        """Analyze all videos and cache results"""
        # Load existing cache
        if not force_refresh and os.path.exists(self.cache_file):
            print(f"Loading cached data from {self.cache_file}")
            self.scan_progress["status"] = "loading_cache"
            self.scan_progress["message"] = "Loading cached data..."
            with open(self.cache_file, 'r') as f:
                self.videos = json.load(f)
            print(f"Loaded {len(self.videos)} videos from cache")
            self.scan_progress["status"] = "complete"
            self.scan_progress["message"] = f"Loaded {len(self.videos)} videos from cache"
            self.scan_progress["total"] = len(self.videos)
            self.scan_progress["processed"] = len(self.videos)

            # Build match graph if it doesn't exist
            if not os.path.exists(self.match_cache_file):
                print("\nBuilding match graph...")
                self.build_match_graph(threshold=15)

            return

        # Scan and analyze all videos
        self.scan_progress["status"] = "scanning"
        self.scan_progress["message"] = "Scanning for video files..."
        video_files = self.scan_videos()
        self.videos = {}

        self.scan_progress["total"] = len(video_files)
        self.scan_progress["processed"] = 0
        self.scan_progress["status"] = "analyzing"

        for i, video_path in enumerate(video_files):
            self.scan_progress["processed"] = i + 1
            self.scan_progress["message"] = f"Analyzing video {i+1}/{len(video_files)}"

            if i % 100 == 0:
                print(f"Progress: {i}/{len(video_files)}")

            try:
                video_data = self.analyze_video(video_path)
                if video_data:
                    # Use relative path as key
                    rel_path = os.path.relpath(video_path, self.video_dir)
                    self.videos[rel_path] = video_data
            except Exception as e:
                print(f"Failed to analyze {video_path}: {e}")

        # Save cache
        print(f"Saving {len(self.videos)} videos to cache...")
        self.scan_progress["status"] = "saving"
        self.scan_progress["message"] = "Saving results to cache..."
        with open(self.cache_file, 'w') as f:
            json.dump(self.videos, f, indent=2)

        print(f"Analysis complete! {len(self.videos)} videos processed")
        self.scan_progress["status"] = "complete"
        self.scan_progress["message"] = f"Analysis complete! {len(self.videos)} videos processed"

        # Build match graph after analysis
        print("\nBuilding match graph...")
        self.build_match_graph(threshold=15)  # Use threshold of 15 for pre-computed matches

    def build_match_graph(self, threshold: int = 15):
        """Pre-compute video matches and store in graph"""
        # Load existing match graph if available
        if os.path.exists(self.match_cache_file):
            try:
                with open(self.match_cache_file, 'r') as f:
                    self.match_graph = json.load(f)
                print(f"Loaded match graph with {len(self.match_graph)} entries")
                return
            except:
                pass

        self.match_graph = {path: [] for path in self.videos.keys()}

        # Group videos by hash prefix for faster matching
        hash_buckets = {}
        for path, data in self.videos.items():
            # Use first 8 characters of hash as bucket key
            bucket_key = data['first_hash'][:8]
            if bucket_key not in hash_buckets:
                hash_buckets[bucket_key] = []
            hash_buckets[bucket_key].append((path, data))

        total = len(self.videos)
        processed = 0

        for path1, data1 in self.videos.items():
            processed += 1
            if processed % 100 == 0:
                print(f"  Processing matches: {processed}/{total}")

            last_hash = data1['last_hash']
            bucket_key = last_hash[:8]

            # Only check videos in nearby buckets
            candidates = hash_buckets.get(bucket_key, [])

            for path2, data2 in candidates:
                if path1 != path2:
                    distance = self.hash_distance(last_hash, data2['first_hash'])
                    if distance <= threshold:
                        self.match_graph[path1].append(path2)

        # Save match graph
        with open(self.match_cache_file, 'w') as f:
            json.dump(self.match_graph, f, indent=2)

        print(f"Match graph built and saved to {self.match_cache_file}")

    def hash_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes"""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except:
            return 999

    def find_chains(self, threshold: int = 15, min_length: int = 2) -> List[List[str]]:
        """Find video chains using pre-computed match graph"""
        print(f"\nFinding chains (min_length={min_length})...")

        # Use pre-computed match graph (already filtered by threshold=15)
        if not self.match_graph:
            # Load match graph if not already loaded
            if os.path.exists(self.match_cache_file):
                with open(self.match_cache_file, 'r') as f:
                    self.match_graph = json.load(f)
            else:
                print("No match graph found. Building...")
                self.build_match_graph(threshold=15)

        # Find all chains using DFS
        visited = set()
        chains = []

        def dfs(path, current_chain):
            visited.add(path)
            current_chain.append(path)

            has_extension = False
            for next_path in self.match_graph.get(path, []):
                if next_path not in visited:
                    has_extension = True
                    dfs(next_path, current_chain.copy())

            if not has_extension and len(current_chain) >= min_length:
                chains.append(current_chain.copy())

            visited.remove(path)

        # Start DFS from each video
        total = len(self.videos)
        processed = 0
        for path in self.videos.keys():
            processed += 1
            if processed % 500 == 0:
                print(f"  Finding chains: {processed}/{total}")
            dfs(path, [])

        # Sort by length (longest first)
        chains.sort(key=len, reverse=True)

        print(f"Found {len(chains)} chains")
        return chains

    def get_chain_info(self, chain: List[str]) -> dict:
        """Get detailed info about a chain"""
        total_duration = sum(self.videos[path]['duration'] for path in chain)

        return {
            "length": len(chain),
            "videos": [
                {
                    "path": path,
                    "filename": self.videos[path]['filename'],
                    "duration": self.videos[path]['duration'],
                    "first_hash": self.videos[path]['first_hash'],
                    "last_hash": self.videos[path]['last_hash']
                }
                for path in chain
            ],
            "total_duration": total_duration
        }


if __name__ == "__main__":
    # Example usage
    video_dir = "/Users/alialqattan/Downloads/8xSovia/https_"
    analyzer = VideoAnalyzer(video_dir)

    # Analyze all videos (or load from cache)
    analyzer.analyze_all(force_refresh=False)

    # Find chains
    chains = analyzer.find_chains(threshold=10, min_length=2)

    # Print top 5 chains
    print("\n=== Top 5 Longest Chains ===")
    for i, chain in enumerate(chains[:5]):
        info = analyzer.get_chain_info(chain)
        print(f"\nChain #{i+1}: {info['length']} videos, {info['total_duration']:.1f}s total")
        for j, video in enumerate(info['videos']):
            print(f"  {j+1}. {video['filename']} ({video['duration']:.1f}s)")
