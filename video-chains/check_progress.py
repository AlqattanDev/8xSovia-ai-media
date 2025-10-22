#!/usr/bin/env python3
"""
Check progress of overnight analysis
Run this anytime to see current status
"""
import os
import json
import time
from datetime import datetime

def format_time(seconds):
    """Format seconds to human readable"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}h {minutes}m {secs}s"

def check_process():
    """Check if analysis process is running"""
    import subprocess
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'run_full_analysis.py'],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except:
        return False

def main():
    print("\n" + "=" * 70)
    print("📊 OVERNIGHT ANALYSIS - PROGRESS CHECK")
    print("=" * 70)
    print()

    # Check if process is running
    is_running = check_process()
    status_icon = "🟢" if is_running else "🔴"
    status_text = "RUNNING" if is_running else "STOPPED"

    print(f"Status: {status_icon} {status_text}")
    print()

    # Check log file
    log_file = "overnight_analysis.log"
    if os.path.exists(log_file):
        print(f"📄 Log file: {log_file}")

        # Get last 10 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()

        print("\n📋 Recent Log Entries (last 10):")
        print("-" * 70)
        for line in lines[-10:]:
            print(line.rstrip())
        print()
    else:
        print("⚠️  No log file found. Analysis may not have started.")
        print()

    # Check cache file
    cache_file = "video_data_smart_FULL.json"
    if os.path.exists(cache_file):
        file_size = os.path.getsize(cache_file) / (1024 * 1024)  # MB
        mod_time = os.path.getmtime(cache_file)
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")

        print(f"💾 Cache file: {cache_file}")
        print(f"   Size: {file_size:.1f} MB")
        print(f"   Last updated: {mod_time_str}")

        # Try to load and count videos
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            videos_analyzed = len(data)
            total_videos = 5453
            progress_pct = (videos_analyzed / total_videos) * 100

            print(f"   Videos analyzed: {videos_analyzed} / {total_videos} ({progress_pct:.1f}%)")

            # Estimate time remaining
            if videos_analyzed > 0 and is_running:
                time_since_start = time.time() - mod_time
                avg_time_per_video = time_since_start / videos_analyzed
                remaining_videos = total_videos - videos_analyzed
                estimated_remaining = avg_time_per_video * remaining_videos

                print(f"   Estimated time remaining: {format_time(estimated_remaining)}")

        except Exception as e:
            print(f"   ⚠️  Could not read cache: {e}")

        print()
    else:
        print("⚠️  No cache file found yet. Analysis may be starting up.")
        print()

    # Check summary
    summary_file = "analysis_summary.json"
    if os.path.exists(summary_file):
        print("✅ Analysis Complete!")
        print()

        with open(summary_file, 'r') as f:
            summary = json.load(f)

        print(f"📊 Results:")
        print(f"   Completion time: {summary['completion_time']}")
        print(f"   Total videos: {summary['total_videos']}")
        print(f"   Total chains: {summary['total_chains']}")
        print(f"   Analysis time: {summary['analysis_time_hours']:.2f} hours")
        print()

        print("🏆 Top 5 Chains:")
        for chain in summary['top_10_chains'][:5]:
            print(f"   {chain['rank']}. Quality: {chain['quality']:.3f} | Length: {chain['length']} videos")
        print()

    print("=" * 70)
    print()
    print("💡 Commands:")
    print("   Monitor logs live:    tail -f overnight_analysis.log")
    print("   Check progress again: python check_progress.py")
    print("   Stop analysis:        pkill -f run_full_analysis.py")
    print()

if __name__ == "__main__":
    main()
