'use client';

import { useEffect } from 'react';

interface HelpModalProps {
  onClose: () => void;
}

export default function HelpModal({ onClose }: HelpModalProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-auto border-2 border-blue-500/50 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 rounded-t-2xl">
          <div className="flex justify-between items-center">
            <h2 className="text-3xl font-bold text-white">
              💡 How It Works
            </h2>
            <button
              onClick={onClose}
              className="text-white hover:text-red-300 text-4xl leading-none transition"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-8 space-y-6">
          {/* What are Chains? */}
          <section>
            <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
              <span className="text-3xl">🔗</span>
              What are Video Chains?
            </h3>
            <div className="bg-white/10 rounded-xl p-6 space-y-3">
              <p className="text-gray-200 text-lg">
                A <strong className="text-blue-400">video chain</strong> is a sequence of videos that flow together naturally. Our AI analyzes your videos and finds ones that connect well when played in order.
              </p>
              <div className="bg-blue-600/20 border-l-4 border-blue-500 p-4 rounded">
                <p className="text-blue-200">
                  <strong>Example:</strong> Video A shows a sunset → Video B shows nighttime → Video C shows stars. These three videos form a natural chain telling a story from dusk to night.
                </p>
              </div>
            </div>
          </section>

          {/* Quality Score */}
          <section>
            <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
              <span className="text-3xl">⭐</span>
              Quality Score Explained
            </h3>
            <div className="bg-white/10 rounded-xl p-6 space-y-4">
              <p className="text-gray-200 text-lg">
                The quality score (0-100%) tells you how well videos connect in a chain. Higher = better connection.
              </p>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-green-600/20 border border-green-500/50 rounded-lg p-4">
                  <div className="text-green-400 font-bold text-xl mb-2">80-100%</div>
                  <div className="text-gray-200">Excellent match! Videos flow perfectly together.</div>
                </div>
                <div className="bg-yellow-600/20 border border-yellow-500/50 rounded-lg p-4">
                  <div className="text-yellow-400 font-bold text-xl mb-2">60-79%</div>
                  <div className="text-gray-200">Good match. Videos connect well with some transitions.</div>
                </div>
                <div className="bg-orange-600/20 border border-orange-500/50 rounded-lg p-4">
                  <div className="text-orange-400 font-bold text-xl mb-2">Below 60%</div>
                  <div className="text-gray-200">Weak match. Videos may not flow smoothly.</div>
                </div>
              </div>
            </div>
          </section>

          {/* How AI Finds Chains */}
          <section>
            <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
              <span className="text-3xl">🧠</span>
              How AI Finds Chains
            </h3>
            <div className="bg-white/10 rounded-xl p-6 space-y-4">
              <p className="text-gray-200 text-lg">
                Our smart system uses 4 different AI signals to find the best connections:
              </p>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-purple-600/20 rounded-lg p-4">
                  <div className="text-purple-400 font-bold mb-2">🎨 Semantic Understanding (30%)</div>
                  <div className="text-gray-300 text-sm">AI understands the <em>meaning</em> of what's in each video - not just pixels, but actual content like "sunset", "ocean", "mountains".</div>
                </div>
                <div className="bg-blue-600/20 rounded-lg p-4">
                  <div className="text-blue-400 font-bold mb-2">🖼️ Frame Matching (40%)</div>
                  <div className="text-gray-300 text-sm">Compares the last frame of one video to the first frame of the next to find visual continuity.</div>
                </div>
                <div className="bg-green-600/20 rounded-lg p-4">
                  <div className="text-green-400 font-bold mb-2">🌈 Color Continuity (15%)</div>
                  <div className="text-gray-300 text-sm">Checks if colors flow smoothly between videos (e.g., both have warm sunset tones).</div>
                </div>
                <div className="bg-yellow-600/20 rounded-lg p-4">
                  <div className="text-yellow-400 font-bold mb-2">🏃 Motion Continuity (15%)</div>
                  <div className="text-gray-300 text-sm">Analyzes how much movement is in each video to find similar pacing.</div>
                </div>
              </div>
            </div>
          </section>

          {/* Using Filters */}
          <section>
            <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
              <span className="text-3xl">🎚️</span>
              Using the Filters
            </h3>
            <div className="bg-white/10 rounded-xl p-6 space-y-4">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="bg-blue-600 rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 text-white font-bold">1</div>
                  <div>
                    <div className="text-white font-semibold">Minimum Quality</div>
                    <div className="text-gray-300 text-sm">Set the lowest quality score you want to see. Higher = fewer but better chains.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="bg-blue-600 rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 text-white font-bold">2</div>
                  <div>
                    <div className="text-white font-semibold">Minimum Chain Length</div>
                    <div className="text-gray-300 text-sm">How many videos must be in a chain? Longer chains = more epic stories.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="bg-blue-600 rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 text-white font-bold">3</div>
                  <div>
                    <div className="text-white font-semibold">Sort By</div>
                    <div className="text-gray-300 text-sm">Choose how to order results - by quality, length, or total duration.</div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Quick Tips */}
          <section>
            <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
              <span className="text-3xl">⚡</span>
              Quick Tips
            </h3>
            <div className="bg-white/10 rounded-xl p-6">
              <ul className="space-y-2 text-gray-200">
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span>Start with 60% minimum quality to see good results</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span>Click "Preview Chain" to watch videos play in sequence</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span>Look for chains with 80%+ quality for the smoothest flow</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span>Each video's match score shows how well it connects to the next one</span>
                </li>
              </ul>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="bg-gray-800/50 p-4 rounded-b-2xl border-t border-gray-700">
          <div className="text-gray-400 text-sm text-center">
            Press ESC to close • Still confused? Try previewing a chain to see it in action!
          </div>
        </div>
      </div>
    </div>
  );
}
