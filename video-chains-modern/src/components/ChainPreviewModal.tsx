'use client';

import { useState, useRef, useEffect } from 'react';
import type { Chain, Video } from '@/types/chain';
import { API_ENDPOINTS } from '@/config/api';

interface ChainPreviewModalProps {
  chain: Chain;
  chainIndex: number;
  onClose: () => void;
}

export default function ChainPreviewModal({ chain, chainIndex, onClose }: ChainPreviewModalProps) {
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const currentVideo = chain.videos[currentVideoIndex];

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleVideoEnd = () => {
    if (currentVideoIndex < chain.videos.length - 1) {
      setCurrentVideoIndex(currentVideoIndex + 1);
    } else {
      setIsPlaying(false);
    }
  };

  const playChain = () => {
    setCurrentVideoIndex(0);
    setIsPlaying(true);
    videoRef.current?.play();
  };

  const togglePlayPause = () => {
    if (videoRef.current?.paused) {
      videoRef.current?.play();
      setIsPlaying(true);
    } else {
      videoRef.current?.pause();
      setIsPlaying(false);
    }
  };

  const goToNext = () => {
    if (currentVideoIndex < chain.videos.length - 1) {
      setCurrentVideoIndex(currentVideoIndex + 1);
      setIsPlaying(true);
    }
  };

  const goToPrevious = () => {
    if (currentVideoIndex > 0) {
      setCurrentVideoIndex(currentVideoIndex - 1);
      setIsPlaying(true);
    }
  };

  useEffect(() => {
    if (isPlaying && videoRef.current) {
      videoRef.current.play().catch(() => setIsPlaying(false));
    }
  }, [currentVideoIndex, isPlaying]);

  return (
    <div
      className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-auto border-2 border-blue-500/50 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 rounded-t-2xl">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">
                Chain #{chainIndex + 1} Preview
              </h2>
              <div className="flex gap-4 text-white/90">
                <span>🎬 {chain.length} videos</span>
                <span>⏱️ {chain.total_duration.toFixed(1)}s total</span>
                <span>⭐ {(chain.avg_quality * 100).toFixed(1)}% quality</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-red-300 text-4xl leading-none transition"
            >
              ×
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="p-6">
          {/* Video Player */}
          <div className="bg-black rounded-xl overflow-hidden mb-6 relative">
            <video
              ref={videoRef}
              src={API_ENDPOINTS.video(currentVideo.path)}
              className="w-full aspect-video"
              onEnded={handleVideoEnd}
              controls
            />

            {/* Video Info Overlay */}
            <div className="absolute top-4 left-4 bg-black/70 backdrop-blur px-4 py-2 rounded-lg">
              <div className="text-white font-bold">
                Video {currentVideoIndex + 1} of {chain.length}
              </div>
              <div className="text-gray-300 text-sm font-mono">
                {currentVideo.filename}
              </div>
            </div>

            {currentVideo.score !== undefined && (
              <div className="absolute top-4 right-4 bg-blue-600/90 backdrop-blur px-4 py-2 rounded-lg">
                <div className="text-white text-sm">Match Score</div>
                <div className="text-white font-bold text-xl">
                  {(currentVideo.score * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={playChain}
              className="flex-1 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition transform hover:scale-105"
            >
              ▶️ Play Entire Chain
            </button>
            <button
              onClick={togglePlayPause}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition"
            >
              {isPlaying ? '⏸️ Pause' : '▶️ Play'}
            </button>
            <button
              onClick={goToPrevious}
              disabled={currentVideoIndex === 0}
              className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition"
            >
              ⏮️ Previous
            </button>
            <button
              onClick={goToNext}
              disabled={currentVideoIndex === chain.length - 1}
              className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition"
            >
              ⏭️ Next
            </button>
          </div>

          {/* Video Timeline */}
          <div className="bg-gray-800/50 rounded-xl p-4">
            <h3 className="text-white font-bold mb-3">Chain Timeline</h3>
            <div className="space-y-2">
              {chain.videos.map((video, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    setCurrentVideoIndex(idx);
                    setIsPlaying(true);
                  }}
                  className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition ${
                    idx === currentVideoIndex
                      ? 'bg-blue-600 shadow-lg scale-105'
                      : 'bg-gray-700/50 hover:bg-gray-700'
                  }`}
                >
                  <div className={`font-bold rounded-full w-8 h-8 flex items-center justify-center text-sm ${
                    idx === currentVideoIndex ? 'bg-white text-blue-600' : 'bg-blue-600 text-white'
                  }`}>
                    {idx + 1}
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
                    <div className="text-blue-300 font-semibold text-sm">
                      {(video.score * 100).toFixed(0)}%
                    </div>
                  )}
                  {idx === currentVideoIndex && (
                    <div className="text-white animate-pulse">▶️</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-800/50 p-4 rounded-b-2xl border-t border-gray-700">
          <div className="text-gray-400 text-sm text-center">
            Press ESC to close • Click video thumbnail to jump to that part
          </div>
        </div>
      </div>
    </div>
  );
}
