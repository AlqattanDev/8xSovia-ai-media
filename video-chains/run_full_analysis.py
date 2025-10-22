#!/usr/bin/env python3
"""
Overnight Full Analysis - All 5,453 Videos
Runs in background with comprehensive logging and progress tracking
"""
import sys
import time
import json
from datetime import datetime
from video_analyzer_smart import SmartVideoAnalyzer

# Logging setup
LOG_FILE = "overnight_analysis.log"

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')

def main():
    log("=" * 80)
    log("🌙 OVERNIGHT FULL ANALYSIS STARTED")
    log("=" * 80)
    log("")

    # Configuration
    video_dir = '/Users/alialqattan/Downloads/8xSovia/https_'
    cache_file = 'video_data_smart_FULL.json'

    log(f"📂 Video Directory: {video_dir}")
    log(f"💾 Cache File: {cache_file}")
    log(f"📊 Expected Videos: 5,453")
    log(f"⏱️  Estimated Time: 7-8 hours")
    log("")

    try:
        # Initialize analyzer
        log("🧠 Initializing Smart Video Analyzer...")
        start_init = time.time()

        analyzer = SmartVideoAnalyzer(video_dir, cache_file=cache_file)

        init_time = time.time() - start_init
        log(f"✅ Analyzer initialized in {init_time:.1f}s")
        log("")

        # Start analysis
        log("🚀 Starting FULL analysis of all videos...")
        log("💡 This will take several hours. You can:")
        log("   • Close this terminal (process keeps running)")
        log("   • Monitor progress: python check_progress.py")
        log("   • Check logs: tail -f overnight_analysis.log")
        log("")

        start_analysis = time.time()

        # Run analysis with progress tracking
        analyzer.analyze_all_smart(force_refresh=True)

        analysis_time = time.time() - start_analysis

        log("")
        log("=" * 80)
        log("✅ ANALYSIS COMPLETE!")
        log("=" * 80)
        log(f"⏱️  Total Time: {analysis_time/3600:.2f} hours ({analysis_time/60:.1f} minutes)")
        log(f"📊 Videos Analyzed: {len(analyzer.videos)}")
        log(f"📁 Results saved to: {cache_file}")
        log(f"⚡ Average Speed: {analysis_time/len(analyzer.videos):.2f}s per video")
        log("")

        # Find chains
        log("🔗 Finding smart chains...")
        start_chains = time.time()

        chains = analyzer.find_smart_chains(min_score=0.6, min_length=3)

        chains_time = time.time() - start_chains

        log(f"✅ Chain discovery complete in {chains_time:.1f}s")
        log(f"📊 Total chains found: {len(chains)}")
        log("")

        # Show top 10 chains
        log("🏆 TOP 10 HIGHEST QUALITY CHAINS:")
        log("-" * 80)
        for i, chain in enumerate(chains[:10]):
            total_duration = sum(analyzer.videos[v]['duration'] for v in chain['videos'])
            log(f"{i+1}. Quality: {chain['avg_quality']:.3f} | "
                f"Length: {chain['length']} videos | "
                f"Duration: {total_duration:.1f}s")

        log("")
        log("=" * 80)
        log("🎉 OVERNIGHT ANALYSIS COMPLETE!")
        log("=" * 80)
        log("")
        log("📚 Next Steps:")
        log("   1. Review results: python review_results.py")
        log("   2. Start API server: python -m uvicorn app:app --port 8001")
        log("   3. Merge top chains: Use the web interface or API")
        log("")
        log(f"✅ Total Runtime: {(time.time() - start_analysis)/3600:.2f} hours")
        log("")

        # Save summary
        summary = {
            "completion_time": datetime.now().isoformat(),
            "total_videos": len(analyzer.videos),
            "total_chains": len(chains),
            "analysis_time_hours": analysis_time/3600,
            "chains_time_seconds": chains_time,
            "top_10_chains": [
                {
                    "rank": i+1,
                    "quality": chain['avg_quality'],
                    "length": chain['length'],
                    "videos": chain['videos']
                }
                for i, chain in enumerate(chains[:10])
            ]
        }

        with open("analysis_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        log("💾 Summary saved to: analysis_summary.json")

    except KeyboardInterrupt:
        log("")
        log("⚠️  Analysis interrupted by user")
        log("💾 Partial results may be saved in cache file")
        sys.exit(1)

    except Exception as e:
        log("")
        log(f"❌ ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
