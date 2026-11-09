/**
 * Ranking explainer configuration thresholds (tag A, UNVERIFIED: team choices).
 * Matches config/ranking.yaml.
 */
export const RANKING_EXPLAINER_CONFIG = {
  /**
   * Criterion must contribute at least this fraction (40%) of the score difference
   * between top and next-best option to be declared the main reason ("mainly because...").
   */
  dominantContributionShare: 0.40,
} as const;
