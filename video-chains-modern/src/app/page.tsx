'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function Home() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetch('http://localhost:8001/api/info')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch stats:', err);
        setLoading(false);
      });
  }, []);

  // Prevent hydration mismatch by not rendering dynamic content until mounted
  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900" suppressHydrationWarning>
        <div className="container mx-auto px-4 py-16">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900" suppressHydrationWarning>
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-6xl font-bold text-white mb-4">
            🧠 Smart Video Chain Finder
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            AI-powered tool that automatically discovers and connects your video clips into meaningful stories
          </p>
        </div>

        {/* What This Does Section */}
        <div className="max-w-4xl mx-auto mb-16 bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
          <h2 className="text-3xl font-bold text-white mb-6">What Does This Do?</h2>
          <div className="space-y-4 text-gray-200 text-lg">
            <p className="flex items-start gap-3">
              <span className="text-2xl">🎬</span>
              <span>
                <strong>Your Videos:</strong> You have <span className="text-blue-400 font-bold">{stats?.videos || '...'}</span> AI-generated video clips
              </span>
            </p>
            <p className="flex items-start gap-3">
              <span className="text-2xl">🔗</span>
              <span>
                <strong>Find Chains:</strong> Our AI finds videos that flow together naturally - like videos that tell a story when played in sequence
              </span>
            </p>
            <p className="flex items-start gap-3">
              <span className="text-2xl">🎯</span>
              <span>
                <strong>Quality Scores:</strong> Each chain gets a quality score (0-100%) showing how well the videos connect
              </span>
            </p>
            <p className="flex items-start gap-3">
              <span className="text-2xl">✨</span>
              <span>
                <strong>Smart Matching:</strong> Unlike just matching frames, we use AI to understand the <em>content</em> and find thematic connections
              </span>
            </p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-16">
          {/* Total Videos */}
          <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-8 shadow-2xl transform hover:scale-105 transition">
            <div className="text-5xl mb-4">🎬</div>
            <div className="text-4xl font-bold text-white mb-2">
              {loading ? '...' : stats?.videos?.toLocaleString() || '0'}
            </div>
            <div className="text-blue-100">Total Videos Analyzed</div>
          </div>

          {/* Smart Mode */}
          <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-2xl p-8 shadow-2xl transform hover:scale-105 transition">
            <div className="text-5xl mb-4">🧠</div>
            <div className="text-4xl font-bold text-white mb-2">
              {stats?.smart_mode ? 'Active' : 'Off'}
            </div>
            <div className="text-purple-100">AI Smart Mode</div>
            {stats?.smart_mode && (
              <div className="mt-2 text-sm text-purple-200">
                ✅ CLIP Semantic Analysis<br/>
                ✅ Multi-Modal Scoring
              </div>
            )}
          </div>

          {/* Chains Ready */}
          <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-2xl p-8 shadow-2xl transform hover:scale-105 transition">
            <div className="text-5xl mb-4">🔗</div>
            <div className="text-4xl font-bold text-white mb-2">
              Ready!
            </div>
            <div className="text-green-100">Chain Discovery Ready</div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="max-w-2xl mx-auto space-y-4">
          <Link href="/discover">
            <button className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold py-6 px-8 rounded-xl shadow-2xl transform hover:scale-105 transition text-xl">
              🔍 Discover Smart Chains →
            </button>
          </Link>

          <a href="http://localhost:8001/docs" target="_blank" rel="noopener noreferrer">
            <button className="w-full bg-gray-700 hover:bg-gray-600 text-white font-bold py-4 px-8 rounded-xl shadow-xl transform hover:scale-105 transition text-lg">
              📖 API Documentation
            </button>
          </a>
        </div>

        {/* Status Banner */}
        {stats && (
          <div className="mt-16 max-w-4xl mx-auto bg-gray-800/50 backdrop-blur rounded-xl p-6 border border-gray-700">
            <h3 className="text-xl font-bold text-white mb-4">System Status</h3>
            <div className="grid md:grid-cols-2 gap-4 text-gray-300">
              <div>
                <strong className="text-white">Version:</strong> {stats.version}
              </div>
              <div>
                <strong className="text-white">Mode:</strong> {stats.message}
              </div>
              <div>
                <strong className="text-white">Frame Matching:</strong> {stats.features?.frame_matching ? '✅' : '❌'}
              </div>
              <div>
                <strong className="text-white">Semantic Matching:</strong> {stats.features?.semantic_matching ? '✅' : '❌'}
              </div>
              <div>
                <strong className="text-white">Scene Detection:</strong> {stats.features?.scene_detection ? '✅' : '❌'}
              </div>
              <div>
                <strong className="text-white">Multi-Modal Scoring:</strong> {stats.features?.multi_modal_scoring ? '✅' : '❌'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-700 mt-16 py-8">
        <div className="container mx-auto px-4 text-center text-gray-400">
          <p>Built with AI • CLIP Semantic Analysis • Multi-Modal Intelligence</p>
        </div>
      </div>
    </div>
  );
}
