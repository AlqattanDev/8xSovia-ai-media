/**
 * API Configuration
 * Centralizes API URL and endpoints
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  info: `${API_URL}/api/info`,
  chains: `${API_URL}/api/chains`,
  smartChains: `${API_URL}/api/chains/smart`,
  video: (path: string) => `${API_URL}/api/video/${path}`,
  progress: `${API_URL}/api/progress`,
  scan: `${API_URL}/api/scan`,
} as const;
