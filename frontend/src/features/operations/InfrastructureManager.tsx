import { apiFetch } from '../../shared/api';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { PlaneLanding, Truck, Route, RefreshCw, Plus, Trash2, Pencil, Activity } from 'lucide-react';
import type { PlannedFlight } from '../planning/FlightPlanner';
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Runway = { id: string; designation: string; length_m: number; separation_min: number; active: boolean };
type Taxiway = { id: string; start_node: number; end_node: number; distance_m: number; active: boolean };
type VehicleKind = 'baggage' | 'fuel' | 'cleaning' | 'catering' | 'tug';
type Vehicle = { id: string; code: string; kind: VehicleKind; speed_kmh: number; capacity_units: number; fuel_pct: number; available: boolean; maintenance: boolean; home_node: number; cost_per_hour: number };
type Task = { id: string; flight_plan_id: string; kind: VehicleKind; duration_min: number; units: number };
type TimelineEvent = { flight_number: string; minute: number; phase: string; details: string; vehicle: string | null };
type ForecastFlight = { flight_number: string; aircraft_registration: string | null; runway: string | null; gate: number | null; status: string; reason: string | null; landing_minute: number | null; takeoff_minute: number | null; delay_min: number };
type Forecast = {
  kpis: {
    flights: number;
    completed: number;
    blocked: number;
    runway_conflicts_avoided: number;
    taxi_conflicts_avoided: number;
    vehicle_missions: number;
    total_delay_min: number;
    taxi_distance_m: number;
    vehicle_distance_m: number;
    estimated_vehicle_cost: number;
  };
  flights: ForecastFlight[];
  timeline: TimelineEvent[];
  note: string;
};
const kinds: VehicleKind[] = ['baggage', 'fuel', 'cleaning', 'catering', 'tug'];
const kindLabels: Record<VehicleKind, string> = { baggage: 'Bagages', fuel: 'Ravitaillement', cleaning: 'Nettoyage', catering: 'Restauration', tug: 'Repoussage' };
const phases: Record<string, string> = { approach: 'Approche', landing: 'Atterrissage', runway_exit: 'Sortie de piste', taxi_in: 'Roulage arrivée', at_gate: 'Au poste', service_start: 'Début du service', service_end: 'Fin du service', pushback: 'Repoussage', taxi_out: 'Roulage départ', takeoff: 'Décollage', blocked: 'Opération bloquée', disruption: 'Perturbation' };
const points: Record<number, [number, number]> = { 0: [38, 130], 1: [190, 130], 2: [310, 20], 3: [310, 75], 4: [310, 130], 5: [310, 185], 6: [310, 240] };
const minutesToClock = (minute: number) => { const value = minute + 360; return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`; };

async function request<T>(path: string, method: string = 'GET', body?: object): Promise<T> {
  const response = await apiFetch(`${API}${path}`, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    const data = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(response.status === 409 ? 'Cet élément existe déjà ou entre en conflit avec un autre.' : (typeof data.detail === 'string' && response.status !== 500 ? data.detail : 'Opération indisponible. Réessayez.'));
  }
  return response.status === 204 ? undefined as T : await response.json() as T;
}

export default function AirportOperations({ plans, simulationMinute }: { plans: PlannedFlight[]; simulationMinute: number }) {
  const [runways, setRunways] = useState<Runway[]>([]);
  const [taxiways, setTaxiways] = useState<Taxiway[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);
  const [runwayDraft, setRunwayDraft] = useState({ designation: '08/26', length_m: 3000, separation_min: 3, active: true });
  const [taxiDraft, setTaxiDraft] = useState({ start_node: 1, end_node: 2, distance_m: 150, active: true });
  const [vehicleDraft, setVehicleDraft] = useState({ code: '', kind: 'baggage' as VehicleKind, speed_kmh: 30, capacity_units: 20, fuel_pct: 100, available: true, maintenance: false, home_node: 1, cost_per_hour: 40 });
  const [taskDraft, setTaskDraft] = useState({ flight_plan_id: '', kind: 'baggage' as VehicleKind, duration_min: 12, units: 1 });
  const [editedVehicle, setEditedVehicle] = useState<string | null>(null);

  async function refresh() {
    setError('');
    try {
      const [r, t, v, k, f] = await Promise.all([
        request<Runway[]>('/api/operations/runways'),
        request<Taxiway[]>('/api/operations/taxiways'),
        request<Vehicle[]>('/api/operations/vehicles'),
        request<Task[]>('/api/operations/tasks'),
        request<Forecast>('/api/operations/forecast')
      ]);
      setRunways(r); setTaxiways(t); setVehicles(v); setTasks(k); setForecast(f);
      } catch { setError('Impossible de charger les opérations. Veuillez réessayer.'); }
  }
  useEffect(() => { void refresh(); }, [plans]);

  async function act(operation: () => Promise<unknown>, message: string) {
    setBusy(true); setError(''); setSuccess('');
    try { await operation(); await refresh(); setSuccess(message); }
    catch (e) { setError(e instanceof Error ? e.message : 'Modification impossible.'); }
    finally { setBusy(false); }
  }
  const handle = (event: FormEvent<HTMLFormElement>, operation: () => Promise<unknown>, message: string) => {
    event.preventDefault(); void act(operation, message);
  };
  const confirmDelete = (label: string, operation: () => Promise<unknown>) => {
    if (window.confirm(`Supprimer ${label} ?`)) void act(operation, 'Élément supprimé.');
  };

  const currentOperations = useMemo(() => {
    if (!forecast) return [];
    return forecast.flights.map(f => {
      const events = forecast.timeline.filter(e => e.flight_number === f.flight_number && e.minute <= simulationMinute);
      return { flight: f, latest: events.at(-1) };
    });
  }, [forecast, simulationMinute]);

  return (
    <section className="airport-operations" aria-label="Infrastructures et services au sol" id="operations">
      <div className="section-title"><h2><Activity size={20} /> Opérations aéroportuaires</h2>
        <button type="button" onClick={() => void refresh()} disabled={busy}><RefreshCw size={15} /> Actualiser les prévisions</button>
      </div>
      <p className="planner-intro">Configurez les pistes, les liaisons de circulation et les véhicules. La prévision ci-dessous complète la simulation des portes avec les étapes d’arrivée, de service et de départ.</p>
      {error && <p role="alert" className="planner-error">{error}</p>}
      {success && <p role="status" className="operation-success">{success}</p>}

      {forecast && <div className="operation-metrics">
        <div><small>Vols terminés</small><strong>{forecast.kpis.completed}/{forecast.kpis.flights}</strong></div>
        <div><small>Interventions</small><strong>{forecast.kpis.vehicle_missions}</strong></div>
        <div><small>Conflits évités</small><strong>{forecast.kpis.runway_conflicts_avoided + (forecast.kpis.taxi_conflicts_avoided ?? 0)}</strong></div>
        <div><small>Opérations bloquées</small><strong>{forecast.kpis.blocked}</strong></div>
        <div><small>Coût véhicules estimé</small><strong>{forecast.kpis.estimated_vehicle_cost.toFixed(2)} €</strong></div>
      </div>}

      <div className="operations-grid">
        <article className="table-card">
          <h3><PlaneLanding size={17} /> Pistes</h3>
          <ul className="operation-rows">{runways.map(r => <li key={r.id}>
            <span><b>{r.designation}</b> · {r.length_m} m · séparation {r.separation_min} min</span>
            <div className="operation-buttons"><button disabled={busy} title={r.active ? 'Fermer la piste' : 'Ouvrir la piste'} onClick={() => void act(() => request(`/api/operations/runways/${r.id}`, 'PATCH', { active: !r.active }), 'Piste mise à jour.')}>{r.active ? 'Ouverte' : 'Fermée'}</button>
            <button aria-label={`Supprimer la piste ${r.designation}`} disabled={busy} onClick={() => confirmDelete(`la piste ${r.designation}`, () => request(`/api/operations/runways/${r.id}`, 'DELETE'))}><Trash2 size={14}/></button></div>
          </li>)}</ul>
          <form className="operation-form" onSubmit={e => handle(e, () => request('/api/operations/runways', 'POST', runwayDraft), 'Piste créée.')}>
            <label>Désignation<input required maxLength={16} value={runwayDraft.designation} onChange={e => setRunwayDraft({ ...runwayDraft, designation: e.target.value.toUpperCase() })}/></label>
            <label>Longueur (m)<input required type="number" min={400} max={6000} value={runwayDraft.length_m} onChange={e => setRunwayDraft({ ...runwayDraft, length_m: Number(e.target.value) })}/></label>
            <label>Séparation (min)<input required type="number" min={1} max={15} value={runwayDraft.separation_min} onChange={e => setRunwayDraft({ ...runwayDraft, separation_min: Number(e.target.value) })}/></label>
            <button className="primary" disabled={busy}><Plus size={14}/> Ajouter la piste</button>
          </form>
        </article>

        <article className="table-card">
          <h3><Route size={17} /> Voies de circulation</h3>
          <p className="planner-intro">0 : piste · 1 : aire de service · 2–6 : portes 1–5. Les liaisons sont bidirectionnelles.</p>
          <svg viewBox="0 0 370 260" role="img" aria-label="Schéma du réseau de circulation" className="taxiway-map">
            {taxiways.map(t => <line key={t.id} x1={points[t.start_node]?.[0]} y1={points[t.start_node]?.[1]} x2={points[t.end_node]?.[0]} y2={points[t.end_node]?.[1]} stroke={t.active ? '#4bd6b4' : '#d36a6a'} strokeWidth={t.active ? 3 : 2} strokeDasharray={t.active ? undefined : '6 5'}/>) }
            {Object.entries(points).map(([id, pos]) => <g key={id}><circle cx={pos[0]} cy={pos[1]} r="13" fill="#1e4553" stroke="#7cc9d1"/><text x={pos[0]} y={pos[1]+4} textAnchor="middle" fill="#fff" fontSize="11">{id}</text></g>)}
          </svg>
          <ul className="operation-rows">{taxiways.map(t => <li key={t.id}>
            <span>{t.start_node} ↔ {t.end_node} · {t.distance_m} m</span>
            <div className="operation-buttons"><button disabled={busy} onClick={() => void act(() => request(`/api/operations/taxiways/${t.id}`, 'PATCH', { active: !t.active }), 'Liaison mise à jour.')}>{t.active ? 'Ouverte' : 'Fermée'}</button>
            <button disabled={busy} aria-label="Supprimer la liaison" onClick={() => confirmDelete(`la liaison ${t.start_node}–${t.end_node}`, () => request(`/api/operations/taxiways/${t.id}`, 'DELETE'))}><Trash2 size={14}/></button></div>
          </li>)}</ul>
          <form className="operation-form" onSubmit={e => handle(e, () => request('/api/operations/taxiways', 'POST', taxiDraft), 'Liaison créée.')}>
            <label>Point A<select value={taxiDraft.start_node} onChange={e => setTaxiDraft({ ...taxiDraft, start_node: Number(e.target.value) })}>{[0,1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
            <label>Point B<select value={taxiDraft.end_node} onChange={e => setTaxiDraft({ ...taxiDraft, end_node: Number(e.target.value) })}>{[0,1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
            <label>Distance (m)<input type="number" min={1} max={10000} value={taxiDraft.distance_m} onChange={e => setTaxiDraft({ ...taxiDraft, distance_m: Number(e.target.value) })}/></label>
            <button className="primary" disabled={busy || taxiDraft.start_node === taxiDraft.end_node}><Plus size={14}/> Ajouter liaison</button>
          </form>
        </article>

        <article className="table-card">
          <h3><Truck size={17}/> Véhicules de service</h3>
          <div className="tablewrap"><table><thead><tr><th>CODE</th><th>TYPE</th><th>CAPACITÉ</th><th>ÉTAT</th><th>ACTIONS</th></tr></thead><tbody>
            {vehicles.map(v => <tr key={v.id}><td><b>{v.code}</b><small>{v.speed_kmh} km/h · {v.fuel_pct}% carburant</small></td><td>{kindLabels[v.kind]}</td><td>{v.capacity_units}</td><td>{v.maintenance ? 'Maintenance' : v.available ? 'Disponible' : 'Indisponible'}</td><td className="planner-actions"><button title="Modifier" disabled={busy} onClick={() => { setEditedVehicle(v.id); setVehicleDraft({ ...v }); }}><Pencil size={14}/></button><button aria-label={`Supprimer ${v.code}`} disabled={busy} onClick={() => confirmDelete(v.code, () => request(`/api/operations/vehicles/${v.id}`, 'DELETE'))}><Trash2 size={14}/></button></td></tr>)}
          </tbody></table></div>
          <form className="operation-form" onSubmit={e => handle(e, async () => { await request(editedVehicle ? `/api/operations/vehicles/${editedVehicle}` : '/api/operations/vehicles', editedVehicle ? 'PATCH' : 'POST', vehicleDraft); setEditedVehicle(null); setVehicleDraft({ code: '', kind: 'baggage', speed_kmh: 30, capacity_units: 20, fuel_pct: 100, available: true, maintenance: false, home_node: 1, cost_per_hour: 40 }); }, editedVehicle ? 'Véhicule modifié.' : 'Véhicule ajouté.')}>
            <label>Code<input required maxLength={24} value={vehicleDraft.code} onChange={e => setVehicleDraft({ ...vehicleDraft, code: e.target.value.toUpperCase() })}/></label>
            <label>Service<select value={vehicleDraft.kind} onChange={e => setVehicleDraft({ ...vehicleDraft, kind: e.target.value as VehicleKind })}>{kinds.map(k => <option key={k} value={k}>{kindLabels[k]}</option>)}</select></label>
            <label>Vitesse (km/h)<input required type="number" min={5} max={120} value={vehicleDraft.speed_kmh} onChange={e => setVehicleDraft({ ...vehicleDraft, speed_kmh: Number(e.target.value) })}/></label>
            <label>Capacité<input required type="number" min={1} max={500} value={vehicleDraft.capacity_units} onChange={e => setVehicleDraft({ ...vehicleDraft, capacity_units: Number(e.target.value) })}/></label>
            <label>Carburant (%)<input required type="number" min={0} max={100} value={vehicleDraft.fuel_pct} onChange={e => setVehicleDraft({ ...vehicleDraft, fuel_pct: Number(e.target.value) })}/></label>
            <label>Coût horaire (€)<input required type="number" min={0} value={vehicleDraft.cost_per_hour} onChange={e => setVehicleDraft({ ...vehicleDraft, cost_per_hour: Number(e.target.value) })}/></label>
            <label className="operation-check"><input type="checkbox" checked={vehicleDraft.available} onChange={e => setVehicleDraft({ ...vehicleDraft, available: e.target.checked })}/> Disponible</label>
            <label className="operation-check"><input type="checkbox" checked={vehicleDraft.maintenance} onChange={e => setVehicleDraft({ ...vehicleDraft, maintenance: e.target.checked })}/> Maintenance</label>
            <button className="primary" disabled={busy}><Plus size={14}/>{editedVehicle ? 'Enregistrer' : 'Ajouter véhicule'}</button>
            {editedVehicle && <button type="button" onClick={() => setEditedVehicle(null)}>Annuler</button>}
          </form>
        </article>

        <article className="table-card">
          <h3>Interventions programmées</h3>
          <p className="planner-intro">Définissez les interventions par vol. Sans intervention personnalisée, les cinq services standard sont utilisés. Le repoussage reste obligatoire.</p>
          <ul className="operation-rows">{tasks.map(t => <li key={t.id}><span><b>{plans.find(f=>f.id === t.flight_plan_id)?.flight_number ?? 'Vol retiré'}</b> · {kindLabels[t.kind]} · {t.duration_min} min · {t.units} unité(s)</span><button disabled={busy} aria-label="Supprimer une intervention" onClick={() => confirmDelete('cette intervention', () => request(`/api/operations/tasks/${t.id}`, 'DELETE'))}><Trash2 size={14}/></button></li>)}</ul>
          <form className="operation-form" onSubmit={e => handle(e, () => request('/api/operations/tasks', 'POST', taskDraft), 'Intervention ajoutée.')}>
            <label>Vol<select required value={taskDraft.flight_plan_id} onChange={e => setTaskDraft({ ...taskDraft, flight_plan_id: e.target.value })}><option value="">Sélectionner…</option>{plans.map(f => <option key={f.id} value={f.id}>{f.flight_number}</option>)}</select></label>
            <label>Opération<select value={taskDraft.kind} onChange={e => setTaskDraft({ ...taskDraft, kind: e.target.value as VehicleKind })}>{kinds.map(k => <option key={k} value={k}>{kindLabels[k]}</option>)}</select></label>
            <label>Durée (min)<input required type="number" min={1} max={180} value={taskDraft.duration_min} onChange={e => setTaskDraft({ ...taskDraft, duration_min: Number(e.target.value) })}/></label>
            <label>Quantité<input required type="number" min={1} max={500} value={taskDraft.units} onChange={e => setTaskDraft({ ...taskDraft, units: Number(e.target.value) })}/></label>
            <button className="primary" disabled={busy || !taskDraft.flight_plan_id}><Plus size={14}/> Ajouter service</button>
          </form>
        </article>
      </div>



      <article className="table-card operation-forecast">
        <div className="section-title"><h3>Suivi des mouvements</h3><span className="minor">Heure simulée : {minutesToClock(simulationMinute)}</span></div>
        <div className="tablewrap"><table><thead><tr><th>VOL</th><th>PISTE</th><th>PORTE</th><th>PHASE COURANTE</th><th>DÉCOLLAGE PRÉVU</th><th>ÉTAT</th></tr></thead><tbody>{currentOperations.map(({flight, latest}) => <tr key={flight.flight_number}><td><b>{flight.flight_number}</b></td><td>{flight.runway ?? '—'}</td><td>{flight.gate == null ? '—' : `P${flight.gate}`}</td><td>{latest ? phases[latest.phase] ?? latest.phase : 'À venir'}</td><td>{flight.takeoff_minute == null ? '—' : minutesToClock(flight.takeoff_minute)}</td><td><span className={flight.status === 'completed' ? 'pill success' : 'pill'}>{flight.reason ?? (flight.status === 'completed' ? 'Planifié' : 'Bloqué')}</span></td></tr>)}</tbody></table></div>
        <h3>Chronologie des événements</h3>
        <ol className="event-timeline">{forecast?.timeline.filter(e => e.minute <= simulationMinute).slice(-35).map((e, i) => <li key={`${e.flight_number}-${e.minute}-${e.phase}-${i}`}><time>{minutesToClock(e.minute)}</time><b>{e.flight_number}</b><span>{phases[e.phase] ?? e.phase} — {e.details}{e.vehicle ? ` (${e.vehicle})` : ''}</span></li>)}</ol>
        {(!forecast || !forecast.timeline.some(e=>e.minute <= simulationMinute)) && <p className="empty">Les événements apparaîtront lorsque la simulation avancera.</p>}
        <p className="planner-intro">Projection déterministe des opérations au sol calculée par le backend Python ; modèle pédagogique simplifié.</p>
      </article>
    </section>
  );
}
