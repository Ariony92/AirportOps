import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Pause, Play, RefreshCw, RotateCcw, SkipForward, AlertTriangle, Gauge, Truck } from 'lucide-react';
import { apiGet } from '../shared/api';
import SceneMap from '../features/simulation/SceneMap';
import { positionAt } from '../features/simulation/display';
import type { Playback } from '../features/simulation/types';

function timeLabel(minute: number) { const value = Math.floor(minute) + 360; return `${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`; }
const rateOptions = [1, 2, 5, 10];

export default function SimulationPage() {
  const [data,setData] = useState<Playback|null>(null);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState('');
  const [playing,setPlaying] = useState(false);
  const [minute,setMinute] = useState(0);
  const [speed,setSpeed] = useState(2);
  const [strategy,setStrategy] = useState<'baseline'|'optimized'>('optimized');
  const [selected,setSelected] = useState<string|null>(null);
  const reload = useCallback(async () => {
    setPlaying(false); setLoading(true); setError('');
    try { const result = await apiGet<Playback>(`/api/operations/playback?strategy=${strategy}`);
      setData(result); setMinute(0); setSelected(null);
    } catch { setError('Impossible de charger la chronologie calculée par le serveur.'); }
    finally { setLoading(false); }
  }, [strategy]);
  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => {
    if (!playing || !data) return;
    const id = window.setInterval(() => setMinute(previous => Math.min(data.duration_minutes, previous + speed / 5)), 200);
    return () => window.clearInterval(id);
  }, [playing, speed, data]);
  useEffect(() => { if (data && minute >= data.duration_minutes) setPlaying(false); }, [minute, data]);
  const recent = useMemo(() => (data?.timeline ?? []).filter(event => event.minute <= minute).slice(-8).reverse(), [data,minute]);
  const current = useMemo(() => selected ? data?.tracks.find(track => track.id === selected) : null, [data,selected]);
  const currentPoint = current ? positionAt(current,minute) : null;
  const activeVehicles = data?.tracks.filter(track => track.kind === 'vehicle' &&
    ['dispatch','service_start','pushback'].includes(positionAt(track,minute)?.phase ?? '')).length ?? 0;
  return <div className="workspace-page">
    <div className="page-heading"><div><p className="eyebrow">CENTRE DE CONTRÔLE</p><h1>Simulation opérationnelle</h1><p>Chaque déplacement et chaque intervention sont issus de la prévision calculée par le serveur.</p></div><button onClick={()=>void reload()} disabled={loading}><RefreshCw size={16}/> Recalculer</button></div>
    <div className="stats-strip">
      <article><Activity size={19}/><small>Vols planifiés</small><strong>{data?.kpis.flights ?? '—'}</strong></article>
      <article><Gauge size={19}/><small>Vols terminés</small><strong>{data?.kpis.completed ?? '—'}</strong></article>
      <article><AlertTriangle size={19}/><small>Retard prévu</small><strong>{data?.kpis.total_delay_min ?? '—'} min</strong></article>
      <article><Truck size={19}/><small>Véhicules en mission</small><strong>{activeVehicles}</strong></article>
    </div>
    <div className="simulation-controls card-pane">
      <div className="controls-left"><button className="primary" onClick={()=>setPlaying(v=>!v)} disabled={!data || loading}>{playing?<Pause size={16}/>:<Play size={16}/>} {playing?'Pause':'Démarrer'}</button>
        <button onClick={()=>{setPlaying(false);setMinute(0);}} aria-label="Revenir au début"><RotateCcw size={16}/></button>
        <button onClick={()=>setMinute(n=>Math.min(data?.duration_minutes ?? 0,n+1))} disabled={!data} aria-label="Avancer d’une minute"><SkipForward size={16}/></button>
        <strong className="sim-clock">{timeLabel(minute)}</strong>
      </div>
      <label>Vitesse <select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{rateOptions.map(value=><option key={value} value={value}>×{value}</option>)}</select></label>
      <label>Stratégie <select value={strategy} onChange={e=>setStrategy(e.target.value as 'baseline'|'optimized')}><option value="optimized">Optimisée</option><option value="baseline">Standard</option></select></label>
    </div>
    <div className="timeline-range"><input type="range" min="0" max={data?.duration_minutes ?? 1} step="0.1" value={minute} onChange={e=>{setPlaying(false);setMinute(Number(e.target.value));}} aria-label="Position dans la simulation" disabled={!data}/><span>{timeLabel(data?.duration_minutes ?? 0)}</span></div>
    {error && <p role="alert" className="planner-error">{error}</p>}
    {loading ? <div className="card-pane">Chargement de la prévision…</div> : data && <>
      <SceneMap tracks={data.tracks} minute={minute} selected={selected} onSelect={setSelected}/>
      <div className="detail-grid">
        <section className="card-pane"><div className="section-title"><h2>Journal des événements</h2><small>Synchronisé avec le temps simulé</small></div>
          {recent.length ? <ol className="event-feed">{recent.map((event,i)=><li key={`${event.flight_number}-${event.minute}-${event.phase}-${i}`}><time>{timeLabel(event.minute)}</time><span><b>{event.flight_number}</b> {event.details}{event.vehicle?` · ${event.vehicle}`:''}</span></li>)}</ol> : <p className="empty">Les opérations commenceront selon leur horaire prévisionnel.</p>}
        </section>
        <section className="card-pane"><h2>Détails de la sélection</h2>{current && currentPoint ? <><strong className="actor-title">{current.label}</strong><p>État : {currentPoint.phase.replaceAll('_',' ')}</p><p>{currentPoint.label}</p></> : <p className="empty">Sélectionner un avion ou un véhicule sur le plan pour suivre son activité.</p>}
          <h3>Règles de lecture</h3><p>Les véhicules restent à l'arrêt tant qu'aucun déplacement ou service n'est prévu. Le curseur est un temps simulé, pas une horloge réelle.</p>
        </section>
      </div>
    </>}
  </div>;
}
