import { useEffect, useState, type FormEvent } from 'react';
import { BookOpen, Plus, Trash2, RefreshCw, Play, Pencil, X, Save } from 'lucide-react';
import { apiGet, apiSend } from '../shared/api';

type ScenarioConfig = { name: string; description: string; delay: number; breakdown: boolean; seed: number };
type Scenario = ScenarioConfig & { id: string; created_at: string };
type Run = {
  id: string; strategy: string; created_at: string;
  result: {
    kpis?: Record<string, number>;
    scenario_inputs?: { delay_minutes: number; breakdown_enabled: boolean; seed: number;
      delayed_flight: string | null; failed_vehicle: string | null };
  };
};
const initial: ScenarioConfig = { name: 'Nouveau scénario', description: '', delay: 0, breakdown: false, seed: 42 };

export default function ScenariosPage() {
  const [items, setItems] = useState<Scenario[]>([]);
  const [draft, setDraft] = useState<ScenarioConfig>({ ...initial });
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);

  async function refresh() {
    try { setItems(await apiGet<Scenario[]>('/api/scenarios')); setError(''); }
    catch { setError('Chargement des scénarios impossible.'); }
  }
  useEffect(() => { void refresh(); }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await apiSend(editing ? `/api/scenarios/${editing}` : '/api/scenarios', editing ? 'PATCH' : 'POST', draft);
      setMessage(editing ? 'Scénario mis à jour.' : 'Scénario enregistré.');
      setDraft({ ...initial }); setEditing(null); await refresh();
    } catch { setError('Enregistrement impossible.'); }
    finally { setBusy(false); }
  }
  function edit(item: Scenario) {
    setEditing(item.id);
    setDraft({ name: item.name, description: item.description, delay: item.delay,
      breakdown: item.breakdown, seed: item.seed });
  }
  async function remove(id: string) {
    if (!window.confirm('Supprimer définitivement ce scénario et ses résultats ?')) return;
    setBusy(true);
    try { await apiSend(`/api/scenarios/${id}`, 'DELETE'); await refresh(); }
    catch { setError('Suppression impossible.'); }
    finally { setBusy(false); }
  }
  async function generate(id: string) {
    setBusy(true); setError('');
    try {
      await apiSend(`/api/scenarios/${id}/generate`, 'POST', { strategy: 'optimized' });
      setMessage('Prévision calculée et enregistrée par le backend.'); await open(id);
    } catch { setError('Calcul de prévision impossible.'); }
    finally { setBusy(false); }
  }
  async function open(id: string) {
    try { setRuns(await apiGet<Run[]>(`/api/scenarios/${id}/runs`)); setExpanded(id); }
    catch { setError('Historique indisponible.'); }
  }

  return <div className="workspace-page">
    <div className="page-heading"><div><p className="eyebrow">HISTORIQUE</p><h1>Scénarios enregistrés</h1>
      <p>Chaque scénario réutilise le planning courant avec ses propres perturbations, calculées sans modifier les données sources.</p></div>
      <button onClick={() => void refresh()}><RefreshCw size={16}/> Actualiser</button>
    </div>
    {error && <p className="planner-error" role="alert">{error}</p>}
    {message && <p className="operation-success" role="status">{message}</p>}
    <form className="card-pane scenario-create" onSubmit={event => void save(event)}>
      <label>Nom du scénario<input required value={draft.name} maxLength={120} onChange={e => setDraft({...draft, name:e.target.value})}/></label>
      <label>Retard d'un vol (min)<input type="number" min={0} max={180} required value={draft.delay} onChange={e => setDraft({...draft, delay:Number(e.target.value)})}/></label>
      <label>Graine aléatoire<input type="number" min={1} max={2147483647} required value={draft.seed} onChange={e => setDraft({...draft, seed:Number(e.target.value)})}/></label>
      <label className="scenario-toggle"><input type="checkbox" checked={draft.breakdown} onChange={e => setDraft({...draft, breakdown:e.target.checked})}/> Panne temporaire d'un véhicule</label>
      <button className="primary" type="submit" disabled={busy || !draft.name.trim()}>{editing ? <Save size={16}/> : <Plus size={16}/>} {editing ? 'Enregistrer' : 'Créer'}</button>
      {editing && <button type="button" onClick={() => {setEditing(null); setDraft({...initial});}}><X size={16}/> Annuler</button>}
    </form>
    <p className="scenario-explanation">La graine choisit de manière reproductible le vol retardé et le véhicule en panne. La panne dure de 06:00 à 10:00 (temps simulé). Les incidents globaux restent pris en compte.</p>
    <div className="scenario-list">{!items.length ? <div className="card-pane empty">Aucun scénario enregistré.</div> : items.map(item =>
      <article key={item.id} className="card-pane scenario-item">
        <div><h2><BookOpen size={17}/>{item.name}</h2><small>{new Date(item.created_at).toLocaleString('fr-FR')}</small>
          <p>Retard : {item.delay} min · Panne : {item.breakdown ? 'oui' : 'non'} · Graine : {item.seed}</p></div>
        <div className="scenario-actions">
          <button onClick={() => edit(item)} disabled={busy}><Pencil size={15}/> Modifier</button>
          <button onClick={() => void open(item.id)}>Historique</button>
          <button onClick={() => void generate(item.id)} disabled={busy}><Play size={15}/> Calculer</button>
          <button onClick={() => void remove(item.id)} disabled={busy} aria-label={`Supprimer ${item.name}`}><Trash2 size={15}/></button>
        </div>
        {expanded === item.id && <div className="scenario-runs">{!runs.length ? <p>Aucune exécution conservée.</p> : runs.map(run =>
          <div key={run.id}><strong>{run.strategy}</strong><span>{new Date(run.created_at).toLocaleString('fr-FR')}</span>
            <span>{run.result.kpis ? `${run.result.kpis.completed ?? 0} vols terminés · ${run.result.kpis.total_delay_min ?? 0} min de retard` : 'Ancien format de résultat'}</span>
            {run.result.scenario_inputs && <span>Vol retardé : {run.result.scenario_inputs.delayed_flight ?? 'aucun'} · Véhicule en panne : {run.result.scenario_inputs.failed_vehicle ?? 'aucun'}</span>}
          </div>)}</div>}
      </article>)}</div>
  </div>;
}
