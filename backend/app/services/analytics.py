"""Operational comparison calculations owned by backend services."""
from typing import Any


def comparison_gains(baseline: dict[str, Any], optimized: dict[str, Any], no_incidents: dict[str, Any]) -> dict[str, Any]:
    base = baseline['kpis']
    improved = optimized['kpis']
    reference = no_incidents['kpis']
    return {
        'delaySavedMinutes': base['total_delay_min'] - improved['total_delay_min'],
        'costSavedEuros': round(base['estimated_vehicle_cost'] - improved['estimated_vehicle_cost'], 2),
        'blockedFlightsAvoided': base['blocked'] - improved['blocked'],
        'incidentDelayDifferenceMinutes': improved['total_delay_min'] - reference['total_delay_min'],
        'delayReductionPercent': round(100 * (base['total_delay_min'] - improved['total_delay_min']) / base['total_delay_min'], 2) if base['total_delay_min'] else None,
    }


# Current runs use server-computed KPI dictionaries. Historical records from the
# previous prototype may contain an older, unverified flat schema.
CURRENT_COMPARE_KEYS = (
    'completed', 'blocked', 'total_delay_min', 'estimated_vehicle_cost',
    'vehicle_missions', 'vehicle_distance_m', 'taxi_distance_m',
    'runway_conflicts_avoided', 'taxi_conflicts_avoided',
)
LEGACY_COMPARE_KEYS = ('total_delay', 'conflicts', 'vehicle_missions', 'vehicle_distance', 'max_delay')


def compare_stored_scenario_runs(first: dict, second: dict) -> tuple[dict, str]:
    current = isinstance(first.get('kpis'), dict) and isinstance(second.get('kpis'), dict)
    legacy = 'kpis' not in first and 'kpis' not in second
    if not current and not legacy:
        raise ValueError('Résultats incompatibles : formats de simulation différents')
    keys = CURRENT_COMPARE_KEYS if current else LEGACY_COMPARE_KEYS
    base = first['kpis'] if current else first
    latest = second['kpis'] if current else second
    if current and any(key not in base or key not in latest for key in keys):
        raise ValueError('Indicateurs absents de la prévision')
    delta = {key: round(latest.get(key, 0) - base.get(key, 0), 2) for key in keys}
    note = ('Calculs issus du moteur métier Python.' if current else
            'Ancien format : les métriques transmises par le client ne sont pas vérifiées.')
    return delta, note
