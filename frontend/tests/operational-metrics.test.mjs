import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateOperationalGains, signed } from '../src/operationalMetrics.ts';

test('compares baseline and optimization without reversing the saving sign', () => {
  const baseline = { completed: 8, blocked: 2, total_delay_min: 140, estimated_vehicle_cost: 218.45 };
  const optimized = { completed: 9, blocked: 1, total_delay_min: 70, estimated_vehicle_cost: 152.28 };
  const withoutIncidents = { completed: 10, blocked: 0, total_delay_min: 25, estimated_vehicle_cost: 135.1 };
  assert.deepEqual(calculateOperationalGains(baseline, optimized, withoutIncidents), {
    delaySavedMinutes: 70,
    costSavedEuros: 66.17,
    blockedFlightsAvoided: 1,
    incidentDelayDifferenceMinutes: 45,
    delayReductionPercent: 50,
  });
});

test('honestly reports regressions and handles a zero-delay baseline', () => {
  const baseline = { completed: 1, blocked: 0, total_delay_min: 0, estimated_vehicle_cost: 1.1 };
  const optimized = { completed: 0, blocked: 1, total_delay_min: 50, estimated_vehicle_cost: 10.6 };
  const comparison = calculateOperationalGains(baseline, optimized, baseline);
  assert.equal(comparison.delaySavedMinutes, -50);
  assert.equal(comparison.costSavedEuros, -9.5);
  assert.equal(comparison.blockedFlightsAvoided, -1);
  assert.equal(comparison.delayReductionPercent, null);
  assert.equal(signed(comparison.costSavedEuros, 2), '-9.50');
  assert.equal(signed(8), '+8');
});

test('does not mutate any metrics passed from a historical snapshot', () => {
  const baseline = Object.freeze({ completed: 7, blocked: 3, total_delay_min: 20, estimated_vehicle_cost: 45.1 });
  const optimized = Object.freeze({ completed: 7, blocked: 3, total_delay_min: 21, estimated_vehicle_cost: 45.1 });
  const without = Object.freeze({ completed: 7, blocked: 3, total_delay_min: 19, estimated_vehicle_cost: 45.1 });
  assert.equal(calculateOperationalGains(baseline, optimized, without).delayReductionPercent, -5);
  assert.equal(baseline.total_delay_min, 20);
  assert.equal(optimized.total_delay_min, 21);
});
