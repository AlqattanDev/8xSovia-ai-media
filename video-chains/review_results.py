#!/usr/bin/env python3
"""
Review results after overnight analysis completes
Shows statistics and top chains
"""
import json
import os

def main():
    print("\n" + "=" * 80)
    print("📊 OVERNIGHT ANALYSIS - RESULTS REVIEW")
    print("=" * 80)
    print()

    # Load cache
    cache_file = "video_data_smart_FULL.json"
    if not os.path.exists(cache_file):
        print("❌ No results found. Run the analysis first:")
        print("   nohup python run_full_analysis.py &")
        return

    print(f"📁 Loading results from: {cache_file}")
    with open(cache_file, 'r') as f:
        videos = json.load(f)

    print(f"✅ Loaded {len(videos)} videos")
    print()

    # Statistics
    print("📊 VIDEO STATISTICS:")
    print("-" * 80)

    total_duration = sum(v['duration'] for v in videos.values())
    avg_duration = total_duration / len(videos)

    motion_scores = [v.get('motion_score', 0) for v in videos.values()]
    avg_motion = sum(motion_scores) / len(motion_scores)

    scene_counts = [v.get('scene_count', 0) for v in videos.values()]
    total_scenes = sum(scene_counts)
    avg_scenes = total_scenes / len(scene_counts)

    has_embeddings = sum(1 for v in videos.values() if v.get('clip_embeddings'))

    print(f"Total videos:         {len(videos)}")
    print(f"Total duration:       {total_duration/3600:.1f} hours")
    print(f"Average duration:     {avg_duration:.1f}s per video")
    print(f"Average motion score: {avg_motion:.2f}")
    print(f"Total scene cuts:     {total_scenes}")
    print(f"Average scenes:       {avg_scenes:.1f} per video")
    print(f"CLIP embeddings:      {has_embeddings} / {len(videos)} ({has_embeddings*100/len(videos):.1f}%)")
    print()

    # Load summary if available
    summary_file = "analysis_summary.json"
    if os.path.exists(summary_file):
        with open(summary_file, 'r') as f:
            summary = json.load(f)

        print("🔗 CHAIN STATISTICS:")
        print("-" * 80)
        print(f"Total chains found:   {summary['total_chains']}")
        print(f"Analysis time:        {summary['analysis_time_hours']:.2f} hours")
        print(f"Chain discovery time: {summary['chains_time_seconds']:.1f} seconds")
        print()

        print("🏆 TOP 10 HIGHEST QUALITY CHAINS:")
        print("-" * 80)
        print(f"{'Rank':<6} {'Quality':<10} {'Length':<8} {'Duration':<12} Preview")
        print("-" * 80)

        for chain in summary['top_10_chains']:
            # Calculate duration
            chain_videos = chain['videos']
            duration = sum(videos[v]['duration'] for v in chain_videos if v in videos)

            # Preview first video
            first_video = chain_videos[0] if chain_videos else ""
            preview = videos.get(first_video, {}).get('filename', 'N/A')[:30]

            print(f"#{chain['rank']:<5} {chain['quality']:<10.3f} "
                  f"{chain['length']:<8} {duration:<12.1f} {preview}...")

        print()
        print("=" * 80)
        print()
        print("🚀 Next Steps:")
        print("   1. Start API server:  python -m uvicorn app:app --port 8001")
        print("   2. View in browser:   http://localhost:8001")
        print("   3. API docs:          http://localhost:8001/docs")
        print("   4. Get smart chains:  curl 'http://localhost:8001/api/chains/smart?min_score=0.7'")
        print()

    else:
        print("⚠️  No summary file found. Analysis may still be running.")
        print("   Check progress: python check_progress.py")
        print()

if __name__ == "__main__":
    main()
