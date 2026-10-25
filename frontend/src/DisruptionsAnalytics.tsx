import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, BarChart3, History, Plus, RotateCcw, Trash2 } from 'lucide-react';
import type { PlannedFlight } from './FlightPlanner';
import { calculateOperationalGains, signed } from './operationalMetrics';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type IncidentKind = 'runway_closure' | 'taxiway_closure' | 'vehicle_failure' | 'flight_delay';
type Strategy = 'baseline' | 'optimized';
type Resource = { id: string; label: string };
type Incident = {
  id: string; kind: IncidentKind; target_id: string;
  start_minute: number; end_minute: number; delay_minutes: number;
  description: string; enabled: boolean;
};
type Kpis = {
  flights: number; completed: number; blocked: number;
  total_delay_min: number; mean_delay_min: number; completion_rate_pct: number;
  estimated_vehicle_cost: number; cost_per_completed_flight: number;
  incident_delay_min: number; configured_incidents: number;
  applied_incidents: number; runway_conflicts_avoided: number;
  taxi_conflicts_avoided: number; vehicle_distance_m: number;
  taxi_distance_m: number;
};
type Forecast = { kpis: Kpis; strategy: Strategy };
type Comparison = {
  baseline: Forecast;
  optimized: Forecast;
  without_incidents: Forecast;
  delta: Record<string, number>;
};
type Snapshot = {
  id: string; label: string; strategy: Strategy;
  incident_count: number; created_at: string; result: Forecast;
};
type Props = {
  flights: PlannedFlight[];
  revision: number;
  runways: Resource[];
  taxiways: Array<{ id: string; start_node: number; end_node: number }>;
  vehicles: Array<{ id: string; code: string }>;
  onChanged: () => Promise<void>;
};

const labels: Record<IncidentKind, string> = {
  runway_closure: 'Fermeture temporaire de piste',
  taxiway_closure: 'Fermeture de voie de circulation',
  vehicle_failure: 'Indisponibilité d’un véhicule',
  flight_delay: 'Retard d’un vol',
};
const kinds: IncidentKind[] = [
  'runway_closure', 'taxiway_closure', 'vehicle_failure', 'flight_delay',
];

function clock(minute: number) {
  const m = minute + 360;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}

async function api<T>(path: string, method = 'GET', body?: object): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({}))) as { detail?: unknown };
    const explanation = typeof detail.detail === 'string' && response.status < 500
      ? detail.detail : 'Impossible de terminer cette opération. Veuillez réessayer.';
    throw new Error(explanation);
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

export default function DisruptionsAnalytics({ flights, runways, taxiways, vehicles, revision, onChanged }: Props) {
  const [kind, setKind] = useState<IncidentKind>('runway_closure');
  const [target, setTarget] = useState('');
  const [begin, setBegin] = useState(15);
  const [end, setEnd] = useState(80);
  const [delay, setDelay] = useState(25);
  const [description, setDescription] = useState('');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [label, setLabel] = useState('Prévision opérationnelle');
  const [saveStrategy, setSaveStrategy] = useState<Strategy>('optimized');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const resources: Record<IncidentKind, Resource[]> = {
    runway_closure: runways,
    taxiway_closure: taxiways.map(t => ({ id: t.id, label: `${t.start_node} ↔ ${t.end_node}` })),
    vehicle_failure: vehicles.map(v => ({ id: v.id, label: v.code })),
    flight_delay: flights.map(f => ({ id: f.id, label: f.flight_number })),
  };
  const available = resources[kind];
  const selectedTarget = available.some(x => x.id === target) ? target : (available[0]?.id ?? '');

  const refresh = useCallback(async () => {
    try {
      const [newIncidents, newComparison, newHistory] = await Promise.all([
        api<Incident[]>('/api/operations/incidents'),
        api<Comparison>('/api/operations/analytics/compare'),
        api<Snapshot[]>('/api/operations/analytics/history?limit=20'),
      ]);
      setIncidents(newIncidents);
      setComparison(newComparison);
      setHistory(newHistory);
      setError('');
    } catch {
      setError('Impossible de charger les incidents et les statistiques pour le moment.');
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh, revision]);

  async function execute(action: () => Promise<unknown>, success: string, updateForecast = true) {
    setBusy(true); setError(''); setMessage('');
    try {
      await action();
      await refresh();
      if (updateForecast) await onChanged();
      setMessage(success);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Modification impossible.');
    } finally {
      setBusy(false);
    }
  }

  function createIncident(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTarget || end <= begin) {
      setError('Choisissez une ressource et une période valide.');
      return;
    }
    void execute(
      () => api('/api/operations/incidents', 'POST', {
        kind, target_id: selectedTarget, start_minute: begin, end_minute: end,
        delay_minutes: kind === 'flight_delay' ? delay : 0, description, enabled: true,
      }),
      'Incident enregistré. Les prévisions ont été recalculées.',
    );
  }

  const resourceName = (item: Incident) => {
    const pool = resources[item.kind];
    return pool.find(r => r.id === item.target_id)?.label ?? 'Ressource archivée';
  };

  const gains = comparison ? calculateOperationalGains(
    comparison.baseline.kpis, comparison.optimized.kpis, comparison.without_incidents.kpis,
  ) : null;

  const lines: Array<{ title: string; key: keyof Kpis; digits?: number }> = [
    { title: 'Vols terminés', key: 'completed' },
    { title: 'Vols bloqués', key: 'blocked' },
    { title: 'Retard total (min)', key: 'total_delay_min' },
    { title: 'Retard moyen (min)', key: 'mean_delay_min', digits: 2 },
    { title: 'Coût des interventions (€)', key: 'estimated_vehicle_cost', digits: 2 },
    { title: 'Coût par vol terminé (€)', key: 'cost_per_completed_flight', digits: 2 },
    { title: 'Distance véhicules (m)', key: 'vehicle_distance_m' },
    { title: 'Conflits piste évités', key: 'runway_conflicts_avoided' },
    { title: 'Conflits circulation évités', key: 'taxi_conflicts_avoided' },
  ];

  return (
    <section className="disruption-section" aria-label="Incidents et analyse opérationnelle">
      <div className="section-title">
        <h2><AlertTriangle size={19} /> Incidents et optimisation</h2>
        <button type="button" disabled={busy} onClick={() => void refresh()}>
          <RotateCcw size={15} /> Actualiser
        </button>
      </div>
      <p className="planner-intro">
        Les incidents sont planifiés sur une période simulée. Les prévisions sont
        recalculées sans modifier les véhicules ni le planning enregistrés.
      </p>
      {error && <p className="planner-error" role="alert">{error}</p>}
      {message && <p className="operation-success" role="status">{message}</p>}

      <div className="disruption-grid">
        <article className="table-card">
          <h3><Plus size={17} /> Programmer un incident</h3>
          <form className="operation-form" onSubmit={createIncident}>
            <label>Type d’incident
              <select value={kind} onChange={e => { setKind(e.target.value as IncidentKind); setTarget(''); }}>
                {kinds.map(x => <option value={x} key={x}>{labels[x]}</option>)}
              </select>
            </label>
            <label>Ressource concernée
              <select required value={selectedTarget} onChange={e => setTarget(e.target.value)}>
                {!available.length && <option value="">Aucune ressource disponible</option>}
                {available.map(x => <option value={x.id} key={x.id}>{x.label}</option>)}
              </select>
            </label>
            <label>Début (minutes après 06:00)
              <input type="number" min="0" max="1439" required value={begin}
                onChange={e => setBegin(Number(e.target.value))} />
            </label>
            <label>Fin (minutes après 06:00)
              <input type="number" min="1" max="1440" required value={end}
                onChange={e => setEnd(Number(e.target.value))} />
            </label>
            {kind === 'flight_delay' && <label>Retard supplémentaire (min)
              <input type="number" min="1" max="180" required value={delay}
                onChange={e => setDelay(Number(e.target.value))} />
            </label>}
            <label>Description
              <input maxLength={240} value={description}
                onChange={e => setDescription(e.target.value)} />
            </label>
            <button className="primary" disabled={busy || !selectedTarget || end <= begin}>
              <Plus size={15} /> Ajouter l’incident
            </button>
          </form>
        </article>

        <article className="table-card">
          <h3><AlertTriangle size={17} /> Incidents enregistrés</h3>
          {incidents.length === 0 && <p className="empty">Aucun incident programmé.</p>}
          <ul className="disruption-list">
            {incidents.map(item => <li key={item.id}>
              <div>
                <strong>{labels[item.kind]}</strong>
                <small>{resourceName(item)} · {clock(item.start_minute)}–{clock(item.end_minute)}</small>
                {item.description && <small>{item.description}</small>}
                <small>{item.enabled ? 'Pris en compte' : 'Désactivé'}</small>
              </div>
              <div className="operation-buttons">
                <button type="button" disabled={busy} aria-label="Changer le statut de l’incident"
                  onClick={() => void execute(() => api(`/api/operations/incidents/${item.id}`, 'PATCH',
                    { kind: item.kind, target_id: item.target_id, start_minute: item.start_minute,
                      end_minute: item.end_minute, delay_minutes: item.delay_minutes,
                      description: item.description, enabled: !item.enabled }),
                    'Incident mis à jour.')}>
                  {item.enabled ? 'Désactiver' : 'Activer'}
                </button>
                <button type="button" disabled={busy} aria-label="Supprimer l’incident"
                  onClick={() => {
                    if (window.confirm('Supprimer cet incident ?'))
                      void execute(() => api(`/api/operations/incidents/${item.id}`, 'DELETE'), 'Incident supprimé.');
                  }}>
                  <Trash2 size={14} />
                </button>
              </div>
            </li>)}
          </ul>
        </article>
      </div>

      <article className="table-card">
        <h3><BarChart3 size={18} /> Analyse comparative</h3>
        <p className="planner-intro">
          Stratégie standard et stratégie optimisée avec incidents,
          comparées à une prévision de référence sans incident.
        </p>
        {gains && <div className="disruption-gains" aria-label="Écarts entre stratégies">
          <div><small>Retard évité par optimisation</small><strong>{signed(gains.delaySavedMinutes)} min</strong></div>
          <div><small>Économie estimée</small><strong>{signed(gains.costSavedEuros, 2)} €</strong></div>
          <div><small>Vols bloqués évités</small><strong>{signed(gains.blockedFlightsAvoided)}</strong></div>
          <div><small>Impact des incidents (retard total)</small><strong>{signed(gains.incidentDelayDifferenceMinutes)} min</strong></div>
        </div>}
        {comparison && <>
          <div className="tablewrap">
            <table>
              <thead><tr>
                <th>INDICATEUR</th><th>STANDARD</th><th>OPTIMISÉE</th><th>SANS INCIDENT</th>
              </tr></thead>
              <tbody>{lines.map(metric => <tr key={metric.key}>
                <td>{metric.title}</td>
                <td>{comparison.baseline.kpis[metric.key].toFixed(metric.digits ?? 0)}</td>
                <td>{comparison.optimized.kpis[metric.key].toFixed(metric.digits ?? 0)}</td>
                <td>{comparison.without_incidents.kpis[metric.key].toFixed(metric.digits ?? 0)}</td>
              </tr>)}</tbody>
            </table>
          </div>
          <p className="planner-intro">
            Incidents actifs : {comparison.optimized.kpis.configured_incidents} ·
            Incidents ayant affecté la prévision : {comparison.optimized.kpis.applied_incidents} ·
            Retard attribué aux incidents : {comparison.optimized.kpis.incident_delay_min} min.
          </p>
        </>}
      </article>

      <article className="table-card">
        <h3><History size={18} /> Historique des prévisions</h3>
        <form className="operation-form" onSubmit={e => {
          e.preventDefault();
          void execute(() => api('/api/operations/analytics/history', 'POST',
            { label: label.trim(), strategy: saveStrategy }), 'Prévision archivée.', false);
        }}>
          <label>Libellé
            <input required maxLength={100} value={label}
              onChange={e => setLabel(e.target.value)} />
          </label>
          <label>Stratégie
            <select value={saveStrategy} onChange={e => setSaveStrategy(e.target.value as Strategy)}>
              <option value="optimized">Optimisée</option>
              <option value="baseline">Standard</option>
            </select>
          </label>
          <button className="primary" disabled={busy || !label.trim()}>
            Enregistrer la prévision
          </button>
        </form>
        <div className="tablewrap">
          <table>
            <thead><tr>
              <th>DATE</th><th>LIBELLÉ</th><th>STRATÉGIE</th>
              <th>INCIDENTS</th><th>VOLS TERMINÉS</th><th>COÛT (€)</th><th>ACTIONS</th>
            </tr></thead>
            <tbody>{history.map(h => <tr key={h.id}>
              <td>{new Date(h.created_at).toLocaleString('fr-FR')}</td>
              <td>{h.label}</td>
              <td>{h.strategy === 'optimized' ? 'Optimisée' : 'Standard'}</td>
              <td>{h.incident_count}</td>
              <td>{h.result.kpis.completed}</td>
              <td>{h.result.kpis.estimated_vehicle_cost.toFixed(2)}</td>
              <td><button aria-label="Supprimer la prévision" type="button" disabled={busy}
                onClick={() => {
                  if (window.confirm('Supprimer cette prévision enregistrée ?'))
                    void execute(() => api(`/api/operations/analytics/history/${h.id}`, 'DELETE'), 'Prévision supprimée.', false);
                }}><Trash2 size={14} /></button></td>
            </tr>)}</tbody>
          </table>
        </div>
        {!history.length && <p className="empty">Aucune prévision archivée.</p>}
      </article>
    </section>
  );
}
