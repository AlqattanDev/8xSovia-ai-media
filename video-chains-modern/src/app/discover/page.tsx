'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import ChainPreviewModal from '@/components/ChainPreviewModal';
import HelpModal from '@/components/HelpModal';

interface Chain {
  length: number;
  avg_quality: number;
  total_duration: number;
  videos: Array<{
    filename: string;
    duration: number;
    score?: number;
  }>;
}

export default function DiscoverPage() {
  const [chains, setChains] = useState<Chain[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(0.6);
  const [minLength, setMinLength] = useState(2);
  const [sortBy, setSortBy] = useState<'quality' | 'length' | 'duration'>('quality');
  const [previewChain, setPreviewChain] = useState<{ chain: Chain; index: number } | null>(null);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    loadChains();
  }, [minScore, minLength]);

  async function loadChains() {
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      const response = await fetch(
        `http://localhost:8001/api/chains/smart?min_score=${minScore}&min_length=${minLength}`,
        { signal: controller.signal }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setChains(data.chains || []);
    } catch (error) {
      console.error('Failed to load chains:', error);

      // Show user-friendly error
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          alert('⏰ Chain discovery is taking longer than expected.\n\n' +
                'The AI is analyzing thousands of videos for the first time.\n' +
                'This initial analysis may take several minutes.\n\n' +
                '💡 TIP: Try raising the "Minimum Quality" slider to 70-80% for faster results.');
        } else {
          alert(`Error loading chains: ${error.message}\n\n` +
                'The backend server may be processing a large dataset.\n' +
                'Please wait a few minutes and try again.');
        }
      }
    } finally {
      setLoading(false);
    }
  }

  const sortedChains = [...chains].sort((a, b) => {
    if (sortBy === 'quality') return b.avg_quality - a.avg_quality;
    if (sortBy === 'length') return b.length - a.length;
    return b.total_duration - a.total_duration;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <div className="border-b border-gray-700 bg-gray-900/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/" className="text-2xl font-bold text-white hover:text-blue-400 transition">
            🧠 Smart Video Chain Finder
          </Link>
          <nav className="flex gap-4">
            <Link href="/" className="text-gray-300 hover:text-white transition">
              Home
            </Link>
            <Link href="/discover" className="text-blue-400 font-semibold">
              Discover
            </Link>
          </nav>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-5xl font-bold text-white mb-4">
            🔍 Discover Smart Chains
          </h1>
          <p className="text-xl text-gray-300">
            Browse AI-discovered video chains with intelligent content matching
          </p>
        </div>

        {/* Filters Panel */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-8 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-6">Filter & Sort</h2>

          <div className="grid md:grid-cols-3 gap-6">
            {/* Minimum Quality */}
            <div>
              <label className="block text-white font-semibold mb-2">
                Minimum Quality: {(minScore * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={minScore * 100}
                onChange={(e) => setMinScore(Number(e.target.value) / 100)}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-sm text-gray-400 mt-1">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Minimum Length */}
            <div>
              <label className="block text-white font-semibold mb-2">
                Minimum Chain Length: {minLength} videos
              </label>
              <input
                type="range"
                min="2"
                max="10"
                value={minLength}
                onChange={(e) => setMinLength(Number(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-sm text-gray-400 mt-1">
                <span>2</span>
                <span>6</span>
                <span>10+</span>
              </div>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-white font-semibold mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                <option value="quality">Highest Quality</option>
                <option value="length">Most Videos</option>
                <option value="duration">Longest Duration</option>
              </select>
            </div>
          </div>

          {/* Results Count */}
          <div className="mt-6 pt-6 border-t border-white/20">
            <div className="text-gray-300">
              {loading ? (
                <span className="animate-pulse">Loading chains...</span>
              ) : (
                <span>
                  Found <strong className="text-blue-400 text-xl">{chains.length}</strong> chains matching your criteria
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Chains Grid */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
            <p className="text-gray-400 mt-4">Discovering smart chains...</p>
          </div>
        ) : chains.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-2xl font-bold text-white mb-2">No Chains Found</h3>
            <p className="text-gray-400">Try adjusting your filters to see more results</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {sortedChains.map((chain, idx) => (
              <ChainCard
                key={idx}
                chain={chain}
                index={idx}
                onPreview={() => setPreviewChain({ chain, index: idx })}
              />
            ))}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewChain && (
        <ChainPreviewModal
          chain={previewChain.chain}
          chainIndex={previewChain.index}
          onClose={() => setPreviewChain(null)}
        />
      )}

      {/* Help Modal */}
      {showHelp && (
        <HelpModal onClose={() => setShowHelp(false)} />
      )}

      {/* Help Button */}
      <button
        onClick={() => setShowHelp(true)}
        className="fixed bottom-8 right-8 bg-gradient-to-br from-blue-600 to-purple-600 text-white p-5 rounded-full shadow-2xl hover:shadow-blue-500/50 hover:scale-110 transition-all duration-300 group"
      >
        <div className="text-3xl">💡</div>
        <div className="absolute bottom-full right-0 mb-2 bg-gray-900 text-white px-3 py-1 rounded-lg text-sm whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
          Help & Tutorial
        </div>
      </button>
    </div>
  );
}

function ChainCard({ chain, index, onPreview }: { chain: Chain; index: number; onPreview: () => void }) {
  const qualityPercent = (chain.avg_quality * 100).toFixed(1);
  const qualityColor = chain.avg_quality >= 0.8 ? 'green' :
                       chain.avg_quality >= 0.6 ? 'yellow' : 'orange';

  const colorClasses = {
    green: 'from-green-600 to-green-700',
    yellow: 'from-yellow-600 to-yellow-700',
    orange: 'from-orange-600 to-orange-700'
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20 hover:border-blue-500 transition transform hover:scale-[1.02]">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">
            Chain #{index + 1}
          </h3>
          <div className="flex gap-4 text-gray-300">
            <span className="flex items-center gap-2">
              🎬 <strong>{chain.length}</strong> videos
            </span>
            <span className="flex items-center gap-2">
              ⏱️ <strong>{chain.total_duration.toFixed(1)}s</strong> total
            </span>
          </div>
        </div>

        {/* Quality Badge */}
        <div className={`bg-gradient-to-br ${colorClasses[qualityColor]} px-6 py-3 rounded-xl shadow-lg`}>
          <div className="text-sm text-white/80 font-semibold">Quality Score</div>
          <div className="text-3xl font-bold text-white">{qualityPercent}%</div>
        </div>
      </div>

      {/* Video List */}
      <div className="mt-4 space-y-2">
        <div className="text-sm font-semibold text-gray-400 mb-2">Videos in this chain:</div>
        {chain.videos.map((video, vidIdx) => (
          <div key={vidIdx} className="flex items-center gap-3 bg-gray-800/50 rounded-lg p-3">
            <div className="bg-blue-600 text-white font-bold rounded-full w-8 h-8 flex items-center justify-center text-sm">
              {vidIdx + 1}
            </div>
            <div className="flex-1">
              <div className="text-white font-mono text-sm truncate">
                {video.filename}
              </div>
              <div className="text-gray-400 text-xs">
                {video.duration.toFixed(1)}s
              </div>
            </div>
            {video.score !== undefined && (
              <div className="text-blue-400 font-semibold text-sm">
                {(video.score * 100).toFixed(0)}%
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="mt-6 flex gap-3">
        <button
          onClick={onPreview}
          className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold py-3 px-6 rounded-xl shadow-lg transition transform hover:scale-105"
        >
          ▶️ Preview Chain
        </button>
        <button className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-xl shadow-lg transition">
          📊 Details
        </button>
      </div>
    </div>
  );
}
