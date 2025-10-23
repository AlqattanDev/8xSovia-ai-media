/**
 * Utility functions for chain quality calculations and display
 */

export type QualityColor = 'green' | 'yellow' | 'orange';

/**
 * Get quality color based on quality score
 * @param quality - Quality score (0-1)
 * @returns Color category
 */
export function getQualityColor(quality: number): QualityColor {
  if (quality >= 0.8) return 'green';
  if (quality >= 0.6) return 'yellow';
  return 'orange';
}

/**
 * Tailwind gradient classes for quality colors
 */
export const QUALITY_COLOR_CLASSES = {
  green: 'from-green-600 to-green-700',
  yellow: 'from-yellow-600 to-yellow-700',
  orange: 'from-orange-600 to-orange-700',
} as const;

/**
 * Get readable quality description
 * @param quality - Quality score (0-1)
 * @returns Description string
 */
export function getQualityDescription(quality: number): string {
  if (quality >= 0.9) return 'Excellent';
  if (quality >= 0.8) return 'Very Good';
  if (quality >= 0.7) return 'Good';
  if (quality >= 0.6) return 'Fair';
  return 'Poor';
}
