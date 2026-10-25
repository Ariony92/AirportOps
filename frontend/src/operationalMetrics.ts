/** Derived comparisons for immutable operational forecast snapshots. */
export type ComparisonKpis = {
  completed: number;
  blocked: number;
  total_delay_min: number;
  estimated_vehicle_cost: number;
};

export type OperationalGains = {
  delaySavedMinutes: number;
  costSavedEuros: number;
  blockedFlightsAvoided: number;
  incidentDelayDifferenceMinutes: number;
  delayReductionPercent: number | null;
};

export function calculateOperationalGains(
  baseline: ComparisonKpis,
  optimized: ComparisonKpis,
  withoutIncidents: ComparisonKpis,
): OperationalGains {
  // Positive numbers are benefits; negative numbers identify regressions.
  return {
    delaySavedMinutes: baseline.total_delay_min - optimized.total_delay_min,
    costSavedEuros: Math.round((baseline.estimated_vehicle_cost - optimized.estimated_vehicle_cost) * 100) / 100,
    blockedFlightsAvoided: baseline.blocked - optimized.blocked,
    incidentDelayDifferenceMinutes: optimized.total_delay_min - withoutIncidents.total_delay_min,
    delayReductionPercent: baseline.total_delay_min === 0
      ? null
      : Math.round(10000 * (baseline.total_delay_min - optimized.total_delay_min) / baseline.total_delay_min) / 100,
  };
}

export function signed(value: number, decimals = 0): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(decimals)}`;
}
