'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import ChainPreviewModal from '@/components/ChainPreviewModal';
import HelpModal from '@/components/HelpModal';
import type { Chain } from '@/types/chain';
import { API_URL } from '@/config/api';
import { getQualityColor, QUALITY_COLOR_CLASSES } from '@/utils/chainUtils';

export default function DiscoverPage() {
  const [chains, setChains] = useState<Chain[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(0.75);  // Default to 75% for faster results
  const [minLength, setMinLength] = useState(2);
  const [sortBy, setSortBy] = useState<'quality' | 'length' | 'duration'>('quality');
  const [previewChain, setPreviewChain] = useState<{ chain: Chain; index: number } | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [showUniqueOnly, setShowUniqueOnly] = useState(true);  // Default to showing unique first frames only

  useEffect(() => {
    loadChains();
  }, [minScore, minLength]);

  async function loadChains() {
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minute timeout for first-time AI processing

      const response = await fetch(
        `${API_URL}/api/chains?min_length=${minLength}`,
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
                '🧠 The AI is computing similarity between all video pairs.\n' +
                '⚡ First-time analysis can take 5-15 minutes.\n' +
                '💾 Results are cached for instant future access.\n\n' +
                '💡 FASTER RESULTS: Use 75-85% quality threshold.\n' +
                '⚠️  Lower quality (below 60%) = MUCH slower processing.');
        } else {
          alert(`Error loading chains: ${error.message}\n\n` +
                '🔧 Backend may be computing AI similarities.\n' +
                '⏱️  First run takes 5-15 minutes (one-time only).\n' +
                '💡 Try 75-80% quality for faster results.');
        }
      }
    } finally {
      setLoading(false);
    }
  }

  // Group chains by first video's first_hash
  const groupedChains = chains.reduce((groups, chain) => {
    const firstHash = chain.videos[0]?.first_hash || 'unknown';
    if (!groups[firstHash]) {
      groups[firstHash] = [];
    }
    groups[firstHash].push(chain);
    return groups;
  }, {} as Record<string, Chain[]>);

  // Get display chains based on unique filter
  let displayChains: Chain[] = [];
  if (showUniqueOnly) {
    // Show only the best chain from each first-frame group
    displayChains = Object.values(groupedChains).map(group => {
      // Sort group by quality and take the best one
      return group.sort((a, b) => b.avg_quality - a.avg_quality)[0];
    });
  } else {
    // Show all chains
    displayChains = chains;
  }

  // Sort the display chains
  const sortedChains = [...displayChains].sort((a, b) => {
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

        {/* Info Banner */}
        <div className="bg-green-600/20 backdrop-blur-lg rounded-2xl p-4 mb-6 border border-green-500/30">
          <div className="flex items-start gap-3">
            <div className="text-3xl">⚡</div>
            <div className="flex-1">
              <h3 className="text-white font-bold mb-1">Fast Frame-Based Chain Discovery</h3>
              <p className="text-green-100 text-sm">
                Using frame similarity matching for instant results! Finds videos with matching visual content.
                Quality filter controls minimum similarity threshold between video frames.
              </p>
            </div>
          </div>
        </div>

        {/* Filters Panel */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-8 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-6">Filter & Sort</h2>

          {/* Unique Filter Toggle */}
          <div className="mb-6 pb-6 border-b border-white/20">
            <label className="flex items-center gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={showUniqueOnly}
                onChange={(e) => setShowUniqueOnly(e.target.checked)}
                className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <div className="flex-1">
                <span className="text-white font-semibold group-hover:text-blue-400 transition">
                  Show only unique starting frames
                </span>
                <p className="text-sm text-gray-400 mt-1">
                  Hide chains that start with the same video frame (recommended for better variety)
                </p>
              </div>
            </label>
          </div>

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
                <div className="space-y-2">
                  <div>
                    Showing <strong className="text-blue-400 text-xl">{sortedChains.length}</strong> chains
                    {showUniqueOnly && chains.length > sortedChains.length && (
                      <span className="text-gray-400">
                        {' '}(filtered from <strong>{chains.length}</strong> total)
                      </span>
                    )}
                  </div>
                  {showUniqueOnly && (
                    <div className="text-sm text-green-400">
                      ✓ Showing only unique starting frames for better variety
                    </div>
                  )}
                </div>
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
            {sortedChains.map((chain, idx) => {
              const firstHash = chain.videos[0]?.first_hash || 'unknown';
              const variantCount = groupedChains[firstHash]?.length || 1;
              return (
                <ChainCard
                  key={idx}
                  chain={chain}
                  index={idx}
                  variantCount={variantCount}
                  onPreview={() => setPreviewChain({ chain, index: idx })}
                />
              );
            })}
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

function ChainCard({ chain, index, variantCount, onPreview }: {
  chain: Chain;
  index: number;
  variantCount: number;
  onPreview: () => void
}) {
  const qualityPercent = (chain.avg_quality * 100).toFixed(1);
  const qualityColor = getQualityColor(chain.avg_quality);

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20 hover:border-blue-500 transition transform hover:scale-[1.02]">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-2xl font-bold text-white">
              Chain #{index + 1}
            </h3>
            {variantCount > 1 && (
              <div className="bg-purple-600/80 backdrop-blur px-3 py-1 rounded-full">
                <span className="text-white text-sm font-semibold">
                  +{variantCount - 1} variant{variantCount > 2 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
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
        <div className={`bg-gradient-to-br ${QUALITY_COLOR_CLASSES[qualityColor]} px-6 py-3 rounded-xl shadow-lg`}>
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
