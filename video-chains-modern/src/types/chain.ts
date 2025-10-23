/**
 * Shared type definitions for video chains
 * Used across discover page, preview modal, and other components
 */

export interface Video {
  path: string;
  filename: string;
  duration: number;
  score?: number;
  first_hash?: string;
  last_hash?: string;
}

export interface Chain {
  length: number;
  avg_quality: number;
  total_duration: number;
  videos: Video[];
}
