"""
Smart Video Chain Analyzer - Enhanced with AI/ML capabilities

This module extends the basic VideoAnalyzer with:
- CLIP embeddings for semantic similarity
- Multi-point frame extraction
- Scene detection
- Weighted chain scoring (multi-modal)
"""
import os
import subprocess
import tempfile
import json
import numpy as np
from pathlib import Path
from PIL import Image
import imagehash
from typing import Dict, List, Tuple, Optional
from video_analyzer import VideoAnalyzer

# Import AI/ML libraries with graceful fallbacks
try:
    import torch
    import open_clip
    CLIP_AVAILABLE = True
except ImportError:
    print("⚠️  CLIP not available. Install: pip install open-clip-torch torch")
    CLIP_AVAILABLE = False

try:
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector
    SCENEDETECT_AVAILABLE = True
except ImportError:
    print("⚠️  SceneDetect not available. Install: pip install scenedetect[opencv]")
    SCENEDETECT_AVAILABLE = False


class SmartVideoAnalyzer(VideoAnalyzer):
    """
    Enhanced video analyzer with semantic understanding and multi-modal matching.

    Key improvements over base VideoAnalyzer:
    1. Multi-point frame extraction (not just first/last)
    2. CLIP embeddings for semantic similarity
    3. Scene detection for better transitions
    4. Weighted scoring combining multiple signals
    """

    def __init__(self, video_dir: str, cache_file: str = "video_data.json",
                 match_cache_file: str = "video_matches.json",
                 use_smart_features: bool = True):
        super().__init__(video_dir, cache_file, match_cache_file)

        self.use_smart_features = use_smart_features and CLIP_AVAILABLE
        self.clip_model = None
        self.clip_preprocess = None
        self.clip_tokenizer = None

        # Weights for multi-modal chain scoring
        self.scoring_weights = {
            'frame_similarity': 0.40,    # Perceptual hash matching (existing)
            'semantic_similarity': 0.30,  # CLIP embedding similarity (NEW)
            'color_continuity': 0.15,     # Color histogram matching (NEW)
            'motion_continuity': 0.15     # Motion pattern matching (NEW)
        }

        if self.use_smart_features:
            print("🧠 Initializing Smart Video Analyzer with AI features...")
            self._load_clip_model()
        else:
            print("📊 Running in basic mode (no CLIP). Install dependencies for smart features.")

    def _load_clip_model(self):
        """Load CLIP model for semantic similarity"""
        if not CLIP_AVAILABLE:
            return

        try:
            print("Loading CLIP model (ViT-B/32)...")
            self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                'ViT-B-32',
                pretrained='openai'
            )
            self.clip_tokenizer = open_clip.get_tokenizer('ViT-B-32')

            # Move to GPU if available
            if torch.cuda.is_available():
                self.clip_model = self.clip_model.cuda()
                print("✅ CLIP model loaded on GPU")
            else:
                print("✅ CLIP model loaded on CPU")

            self.clip_model.eval()
        except Exception as e:
            print(f"❌ Failed to load CLIP model: {e}")
            self.use_smart_features = False

    def get_clip_embedding(self, image: Image.Image) -> Optional[np.ndarray]:
        """Extract CLIP embedding from image"""
        if not self.use_smart_features or self.clip_model is None:
            return None

        try:
            # Preprocess and encode
            image_input = self.clip_preprocess(image).unsqueeze(0)

            if torch.cuda.is_available():
                image_input = image_input.cuda()

            with torch.no_grad():
                embedding = self.clip_model.encode_image(image_input)
                embedding = embedding.cpu().numpy().flatten()

            # Normalize
            embedding = embedding / np.linalg.norm(embedding)

            return embedding
        except Exception as e:
            print(f"Error extracting CLIP embedding: {e}")
            return None

    def extract_color_histogram(self, image: Image.Image, bins: int = 32) -> np.ndarray:
        """Extract color histogram for color continuity analysis"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize for consistency
            image = image.resize((256, 256))

            # Extract histograms for each channel
            pixels = np.array(image)
            hist_r = np.histogram(pixels[:,:,0], bins=bins, range=(0, 256))[0]
            hist_g = np.histogram(pixels[:,:,1], bins=bins, range=(0, 256))[0]
            hist_b = np.histogram(pixels[:,:,2], bins=bins, range=(0, 256))[0]

            # Concatenate and normalize
            histogram = np.concatenate([hist_r, hist_g, hist_b])
            histogram = histogram / np.sum(histogram)

            return histogram
        except Exception as e:
            print(f"Error extracting color histogram: {e}")
            return np.zeros(bins * 3)

    def estimate_motion_score(self, video_path: str) -> float:
        """
        Estimate motion/action level in video.
        Higher score = more motion/action
        """
        try:
            # Extract 3 frames at different positions
            duration = self.get_video_duration(video_path)
            if not duration:
                return 0.5  # Default mid-level motion

            frame1 = self.extract_frame(video_path, str(duration * 0.25))
            frame2 = self.extract_frame(video_path, str(duration * 0.50))
            frame3 = self.extract_frame(video_path, str(duration * 0.75))

            if not all([frame1, frame2, frame3]):
                return 0.5

            # Compute hash differences between consecutive frames
            hash1 = imagehash.average_hash(frame1)
            hash2 = imagehash.average_hash(frame2)
            hash3 = imagehash.average_hash(frame3)

            diff1 = hash1 - hash2
            diff2 = hash2 - hash3

            # Average difference (higher = more motion)
            avg_diff = (diff1 + diff2) / 2

            # Normalize to 0-1 range (assuming max diff is ~64 for 8x8 hash)
            motion_score = min(1.0, avg_diff / 32.0)

            return motion_score
        except Exception as e:
            print(f"Error estimating motion: {e}")
            return 0.5

    def detect_scenes(self, video_path: str) -> List[float]:
        """
        Detect scene boundaries in video.
        Returns list of timestamps where scenes change.
        """
        if not SCENEDETECT_AVAILABLE:
            return []

        try:
            video = open_video(video_path)
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=27.0))

            # Detect scenes
            scene_manager.detect_scenes(video)
            scene_list = scene_manager.get_scene_list()

            # Extract timestamps
            timestamps = [scene[0].get_seconds() for scene in scene_list]

            return timestamps
        except Exception as e:
            print(f"Error detecting scenes in {video_path}: {e}")
            return []

    def analyze_video_smart(self, video_path: str) -> Optional[dict]:
        """
        Enhanced video analysis with multi-modal features.

        Returns comprehensive video data including:
        - Basic info (duration, size, etc.)
        - Frame hashes (first, middle, last)
        - CLIP embeddings for semantic matching
        - Color histograms for visual continuity
        - Motion score for action matching
        - Scene boundaries
        """
        print(f"🔍 Smart analyzing: {os.path.basename(video_path)}")

        # Get basic analysis from parent class
        basic_data = self.analyze_video(video_path)
        if not basic_data:
            return None

        # Get duration
        duration = basic_data.get('duration')
        if not duration:
            return basic_data

        try:
            # Extract frames at multiple points (0%, 50%, 100%)
            timestamps = [0, duration * 0.5, duration - 0.1]
            frames = []
            hashes = []
            clip_embeddings = []
            color_histograms = []

            for ts in timestamps:
                frame = self.extract_frame(video_path, str(ts))
                if frame:
                    frames.append(frame)
                    hashes.append(str(self.compute_hash(frame)))

                    # CLIP embedding
                    if self.use_smart_features:
                        embedding = self.get_clip_embedding(frame)
                        if embedding is not None:
                            clip_embeddings.append(embedding.tolist())

                    # Color histogram
                    color_hist = self.extract_color_histogram(frame)
                    color_histograms.append(color_hist.tolist())

            # Detect scenes
            scenes = self.detect_scenes(video_path) if SCENEDETECT_AVAILABLE else []

            # Estimate motion
            motion_score = self.estimate_motion_score(video_path)

            # Enhanced data structure
            enhanced_data = {
                **basic_data,
                'frames': {
                    'first_hash': hashes[0] if len(hashes) > 0 else basic_data['first_hash'],
                    'middle_hash': hashes[1] if len(hashes) > 1 else None,
                    'last_hash': hashes[-1] if len(hashes) > 0 else basic_data['last_hash'],
                },
                'clip_embeddings': clip_embeddings if clip_embeddings else None,
                'color_histograms': color_histograms,
                'motion_score': motion_score,
                'scene_count': len(scenes),
                'scene_timestamps': scenes[:5],  # Limit to first 5 scenes
                'smart_analysis': self.use_smart_features
            }

            return enhanced_data

        except Exception as e:
            print(f"Error in smart analysis: {e}")
            return basic_data

    def compute_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two CLIP embeddings"""
        try:
            embedding1 = np.array(embedding1)
            embedding2 = np.array(embedding2)

            # Cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )

            # Convert to 0-1 range (cosine is -1 to 1)
            similarity = (similarity + 1) / 2

            return float(similarity)
        except Exception as e:
            print(f"Error computing semantic similarity: {e}")
            return 0.0

    def compute_color_similarity(self, hist1: np.ndarray, hist2: np.ndarray) -> float:
        """Compute color histogram similarity"""
        try:
            hist1 = np.array(hist1)
            hist2 = np.array(hist2)

            # Chi-square distance
            chi_square = np.sum((hist1 - hist2) ** 2 / (hist1 + hist2 + 1e-10))

            # Convert to similarity (lower distance = higher similarity)
            similarity = 1.0 / (1.0 + chi_square)

            return float(similarity)
        except Exception as e:
            print(f"Error computing color similarity: {e}")
            return 0.0

    def compute_chain_score(self, video1_data: dict, video2_data: dict) -> dict:
        """
        Compute multi-modal chain score between two videos.

        Returns:
            dict with individual scores and weighted final score
        """
        scores = {
            'frame_similarity': 0.0,
            'semantic_similarity': 0.0,
            'color_continuity': 0.0,
            'motion_continuity': 0.0,
            'final_score': 0.0
        }

        try:
            # 1. Frame similarity (existing method)
            if 'frames' in video1_data and 'frames' in video2_data:
                last_hash = video1_data['frames']['last_hash']
                first_hash = video2_data['frames']['first_hash']
                distance = self.hash_distance(last_hash, first_hash)
                # Convert to similarity (lower distance = higher similarity)
                scores['frame_similarity'] = max(0, 1.0 - distance / 64.0)

            # 2. Semantic similarity (CLIP embeddings)
            if (self.use_smart_features and
                video1_data.get('clip_embeddings') and
                video2_data.get('clip_embeddings')):
                emb1 = video1_data['clip_embeddings'][-1]  # Last frame
                emb2 = video2_data['clip_embeddings'][0]   # First frame
                scores['semantic_similarity'] = self.compute_semantic_similarity(emb1, emb2)

            # 3. Color continuity
            if (video1_data.get('color_histograms') and
                video2_data.get('color_histograms')):
                hist1 = video1_data['color_histograms'][-1]
                hist2 = video2_data['color_histograms'][0]
                scores['color_continuity'] = self.compute_color_similarity(hist1, hist2)

            # 4. Motion continuity
            if 'motion_score' in video1_data and 'motion_score' in video2_data:
                motion_diff = abs(video1_data['motion_score'] - video2_data['motion_score'])
                scores['motion_continuity'] = 1.0 - motion_diff

            # Compute weighted final score
            final_score = sum(
                scores[key] * self.scoring_weights[key]
                for key in self.scoring_weights.keys()
            )
            scores['final_score'] = final_score

        except Exception as e:
            print(f"Error computing chain score: {e}")

        return scores

    def analyze_all_smart(self, force_refresh: bool = False, sample_size: Optional[int] = None):
        """
        Analyze all videos with smart features.

        Args:
            force_refresh: Re-analyze even if cache exists
            sample_size: Only analyze first N videos (for testing)
        """
        # Load existing cache if available
        if not force_refresh and os.path.exists(self.cache_file):
            print(f"Loading cached data from {self.cache_file}")
            with open(self.cache_file, 'r') as f:
                cached_data = json.load(f)

            # Check if cache has smart features
            sample = next(iter(cached_data.values()))
            if sample.get('smart_analysis'):
                print(f"✅ Cache has smart features. Loaded {len(cached_data)} videos.")
                self.videos = cached_data
                return
            else:
                print("⚠️  Cache exists but lacks smart features. Re-analyzing...")

        # Scan videos
        video_files = self.scan_videos()

        if sample_size:
            video_files = video_files[:sample_size]
            print(f"📊 Sample mode: Analyzing {sample_size} videos")

        self.videos = {}
        total = len(video_files)

        print(f"\n🚀 Starting smart analysis of {total} videos...")

        for i, video_path in enumerate(video_files):
            if i % 10 == 0:
                print(f"Progress: {i}/{total} ({i*100//total}%)")

            try:
                video_data = self.analyze_video_smart(video_path)
                if video_data:
                    rel_path = os.path.relpath(video_path, self.video_dir)
                    self.videos[rel_path] = video_data
            except Exception as e:
                print(f"Failed to analyze {video_path}: {e}")

        # Save cache
        print(f"\n💾 Saving {len(self.videos)} videos to cache...")
        with open(self.cache_file, 'w') as f:
            json.dump(self.videos, f, indent=2)

        print(f"✅ Smart analysis complete! {len(self.videos)} videos processed")

    def _build_similarity_graph(self, min_score: float = 0.6, cache_file: str = "similarity_graph_cache.json") -> Dict[str, List[Tuple[str, dict]]]:
        """
        Pre-compute similarity scores between all video pairs above threshold.
        Uses disk caching to avoid recomputation.

        Returns:
            Dictionary mapping each video path to list of (next_video_path, scores) tuples
        """
        # Try to load from cache first
        if os.path.exists(cache_file):
            try:
                print(f"📂 Loading similarity graph from cache ({cache_file})...")
                with open(cache_file, 'r') as f:
                    cached_graph = json.load(f)

                # Check if cache is for the same min_score and video count
                cache_info = cached_graph.get('_cache_info', {})
                if (cache_info.get('min_score') == min_score and
                    cache_info.get('num_videos') == len(self.videos)):
                    print(f"✅ Loaded cached similarity graph with {sum(len(v) for v in cached_graph['graph'].values() if isinstance(v, list))} edges")
                    return cached_graph['graph']
                else:
                    print("⚠️  Cache outdated (different parameters or video count), rebuilding...")
            except Exception as e:
                print(f"⚠️  Failed to load cache: {e}, rebuilding...")

        print(f"📊 Pre-computing similarity graph (threshold={min_score})...")
        print(f"⚠️  WARNING: This may take a LONG time for {len(self.videos)} videos!")
        print(f"💡 TIP: Consider using a higher min_score (e.g., 0.7-0.8) for faster initial results")

        similarity_graph = {}
        video_paths = list(self.videos.keys())
        total = len(video_paths)

        # Use multiprocessing for faster computation
        import time
        start_time = time.time()

        for i, path1 in enumerate(video_paths):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                est_total = (elapsed / max(i, 1)) * total
                print(f"  Progress: {i}/{total} ({i/total*100:.1f}%) - Elapsed: {elapsed/60:.1f}min, ETA: {(est_total-elapsed)/60:.1f}min")

            video1_data = self.videos[path1]
            candidates = []

            # Only compute forward connections (path1 -> path2)
            for path2 in video_paths:
                if path1 != path2:
                    video2_data = self.videos[path2]
                    chain_scores = self.compute_chain_score(video1_data, video2_data)

                    if chain_scores['final_score'] >= min_score:
                        candidates.append((path2, chain_scores))

            # Sort by score and keep only top matches
            candidates.sort(key=lambda x: x[1]['final_score'], reverse=True)
            similarity_graph[path1] = candidates[:20]  # Keep top 20 matches per video

        total_edges = sum(len(v) for v in similarity_graph.values())
        print(f"✅ Similarity graph built with {total_edges} edges in {(time.time()-start_time)/60:.1f} minutes")

        # Save to cache
        try:
            print(f"💾 Saving similarity graph to cache...")
            cache_data = {
                '_cache_info': {
                    'min_score': min_score,
                    'num_videos': len(self.videos),
                    'total_edges': total_edges,
                    'created_at': time.time()
                },
                'graph': similarity_graph
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            print(f"✅ Cache saved to {cache_file}")
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")

        return similarity_graph

    def find_smart_chains(self, min_score: float = 0.6, min_length: int = 2, max_starting_points: int = 500) -> List[dict]:
        """
        Find chains using multi-modal scoring with pre-computed similarity graph.

        Args:
            min_score: Minimum chain quality score (0-1)
            min_length: Minimum number of videos in chain
            max_starting_points: Maximum number of videos to use as chain starting points

        Returns:
            List of chains with quality scores
        """
        print(f"\n🔗 Finding smart chains (min_score={min_score}, min_length={min_length})...")

        # Pre-compute similarity graph (MAJOR OPTIMIZATION)
        similarity_graph = self._build_similarity_graph(min_score)

        # Build weighted similarity graph
        chains = []
        visited = set()

        def dfs(path, current_chain, scores):
            visited.add(path)
            current_chain.append(path)

            # Get pre-computed candidates from similarity graph
            candidates = []
            if path in similarity_graph:
                for next_path, chain_scores in similarity_graph[path]:
                    if next_path not in visited:
                        candidates.append((next_path, chain_scores))

            has_extension = False
            for next_path, chain_scores in candidates[:5]:  # Limit branching
                has_extension = True
                new_scores = scores + [chain_scores]
                dfs(next_path, current_chain.copy(), new_scores)

            if not has_extension and len(current_chain) >= min_length:
                # Calculate average chain quality
                avg_score = np.mean([s['final_score'] for s in scores]) if scores else 0

                chains.append({
                    'videos': current_chain.copy(),
                    'length': len(current_chain),
                    'scores': scores,
                    'avg_quality': avg_score
                })

            visited.remove(path)

        # Start DFS from videos with the most connections (most promising starting points)
        video_rankings = [(path, len(similarity_graph.get(path, []))) for path in self.videos.keys()]
        video_rankings.sort(key=lambda x: x[1], reverse=True)

        starting_points = min(max_starting_points, len(video_rankings))
        print(f"🚀 Starting chain search from {starting_points} most connected videos...")

        for i, (path, num_connections) in enumerate(video_rankings[:starting_points]):
            if i % 50 == 0:
                print(f"  Progress: {i}/{starting_points} starting points explored, {len(chains)} chains found")
            dfs(path, [], [])

        # Sort by quality and length
        chains.sort(key=lambda x: (x['avg_quality'], x['length']), reverse=True)

        print(f"✅ Found {len(chains)} smart chains")
        return chains[:100]  # Return top 100


if __name__ == "__main__":
    # Test smart analyzer
    video_dir = "/Users/alialqattan/Downloads/8xSovia/https_"

    print("🧪 Testing Smart Video Analyzer\n")
    print("=" * 60)

    # Create analyzer
    analyzer = SmartVideoAnalyzer(video_dir, cache_file="video_data_smart.json")

    # Analyze sample (first 10 videos for testing)
    print("\n📊 Analyzing sample of 10 videos...")
    analyzer.analyze_all_smart(force_refresh=True, sample_size=10)

    # Find smart chains
    print("\n🔗 Finding smart chains...")
    chains = analyzer.find_smart_chains(min_score=0.5, min_length=2)

    # Display results
    print(f"\n📈 RESULTS:")
    print(f"Total videos analyzed: {len(analyzer.videos)}")
    print(f"Chains found: {len(chains)}")

    if chains:
        print(f"\n🏆 Top 3 Highest Quality Chains:")
        for i, chain in enumerate(chains[:3]):
            print(f"\nChain #{i+1}:")
            print(f"  Length: {chain['length']} videos")
            print(f"  Avg Quality: {chain['avg_quality']:.2f}")
            print(f"  Videos:")
            for j, video_path in enumerate(chain['videos']):
                video_data = analyzer.videos[video_path]
                print(f"    {j+1}. {video_data['filename']}")
