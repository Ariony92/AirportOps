import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  Plane,
  Truck,
  CalendarClock,
  Play,
  Pause,
  RotateCcw,
  Save,
  GitCompareArrows,
  AlertTriangle,
  Clock3,
  Database,
  Download,
  ChevronRight,
  Trash2,
} from 'lucide-react';
import {
  createSimulator,
  DemoSimulator,
  type Flight,
  type Simulator,
  type Stats,
} from './simulation';
import FlightPlanner, { type PlannedFlight } from './FlightPlanner';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Scenario = {
  id: string;
  name: string;
  description: string;
  delay: number;
  breakdown: boolean;
  seed: number;
};

const initStats: Stats = {
  finished: 0,
  total_delay: 0,
  conflicts: 0,
  vehicle_missions: 0,
  vehicle_distance: 0,
  max_delay: 0,
};

function formatTime(minutes: number) {
  if (minutes < 0) return '—';
  const m = minutes + 360;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}

function AirportMap({ flights, time }: { flights: Flight[]; time: number }) {
  const gates = Array.from({ length: 5 }, (_, i) => i);

  return (
    <div className="map">
      <div className="map-heading">
        <span>● SIMULATION EN DIRECT</span>
        <span>AÉROPORT FICTIF</span>
      </div>

      <svg
        viewBox="0 0 900 470"
        role="img"
        aria-label="Vue aérienne schématique de l'aéroport avec ses portes, avions et voies de circulation"
      >
        <defs>
          <pattern id="lines" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M30 0H0V30" fill="none" stroke="#253d4b" strokeWidth=".7" />
          </pattern>
        </defs>

        <rect width="900" height="470" fill="#0c2230" />
        <rect width="900" height="470" fill="url(#lines)" />
        <rect x="0" y="355" width="900" height="70" rx="5" fill="#223540" />
        <path d="M0 390H900" stroke="#e8c981" strokeWidth="2" strokeDasharray="24 19" />
        <text x="24" y="380" fill="#e0bd76" fontSize="11" fontWeight="bold">
          PISTE 09/27
        </text>

        <rect x="40" y="37" width="820" height="60" rx="10" fill="#243b4a" stroke="#455e69" />
        <text x="450" y="60" fill="#aebfc8" textAnchor="middle" fontSize="12" fontWeight="bold" letterSpacing="3">
          TERMINAL 1
        </text>
        <text x="450" y="80" fill="#748d9c" textAnchor="middle" fontSize="10">
          AIRPORTOPS INTERNATIONAL
        </text>

        <path d="M50 286H850" stroke="#d4af63" strokeWidth="3" strokeDasharray="12 9" />
        <path d="M450 286V355" stroke="#d4af63" strokeWidth="2" strokeDasharray="8 8" />

        {gates.map((gate) => {
          const x = 112 + gate * 170;
          const active = flights.filter(
            (flight) =>
              flight.completed &&
              flight.gate === gate &&
              time >= (flight.service_start ?? flight.arrival) &&
              time < flight.departure
          );

          return (
            <g key={gate}>
              <path d={`M${x} 97V286`} stroke="#355565" strokeWidth="8" />
              <path d={`M${x} 97V286`} stroke="#c0a768" strokeWidth="1.5" strokeDasharray="7 8" />
              <rect
                x={x - 57}
                y="111"
                width="114"
                height="115"
                rx="8"
                fill={active.length ? '#163f4c' : '#142d3a'}
                stroke={active.length ? '#3bbf9c' : '#456473'}
                strokeWidth="2"
                strokeDasharray={active.length ? '0' : '5 5'}
              />
              <text x={x} y="132" textAnchor="middle" fill="#bad0d8" fontSize="12" fontWeight="bold">
                PORTE {String(gate + 1).padStart(2, '0')}
              </text>

              {active.length ? (
                <g transform={`translate(${x},185) rotate(-90)`}>
                  <path
                    d="M-9-49L-5-47L-2-12L38-6L42-1L-2 5L-5 48L-9 51L-13 6L-36 5L-39 0L-36-5L-13-12Z"
                    fill="#66e2bd"
                    stroke="#e4fff5"
                    strokeWidth="1.5"
                  />
                </g>
              ) : (
                <text x={x} y="187" fill="#657f8b" textAnchor="middle" fontSize="12">
                  LIBRE
                </text>
              )}
            </g>
          );
        })}

        <g transform={`translate(${200 + (time * 2) % 490},302)`}>
          <rect x="-15" y="-9" rx="4" width="30" height="18" fill="#e2aa54" />
          <rect x="-8" y="-12" width="15" height="8" rx="2" fill="#f2ce89" />
          <circle cx="-9" cy="11" r="4" fill="#0a1217" />
          <circle cx="9" cy="11" r="4" fill="#0a1217" />
        </g>

        <text x="35" y="450" fill="#7699a9" fontSize="11">AIRE DE STATIONNEMENT</text>
        <text x="865" y="450" fill="#7699a9" fontSize="11" textAnchor="end">
          VUE SCHÉMATIQUE • NON À L’ÉCHELLE
        </text>
      </svg>

      <div className="map-bottom">
        <span><i className="dot green" /> Avion au poste</span>
        <span><i className="dot amber" /> Véhicule au sol</span>
        <span><i className="dot slate" /> Porte libre</span>
      </div>
    </div>
  );
}

export default function App() {
  const engine = useRef<Simulator>(new DemoSimulator());

  const [mode, setMode] = useState('Initialisation');
  const [running, setRunning] = useState(false);
  const [time, setTime] = useState(0);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [stats, setStats] = useState<Stats>(initStats);
  const [strategy, setStrategy] = useState(1);
  const [delay, setDelay] = useState(30);
  const [breakdown, setBreakdown] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [name, setName] = useState('Scénario de démonstration');
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState('');
  const [removingScenarioId, setRemovingScenarioId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [scenariosError, setScenariosError] = useState('');
  const [comparison, setComparison] = useState<{ baseline: Stats; optimized: Stats } | null>(null);
  const [planning, setPlanning] = useState<PlannedFlight[]>([]);
  const planningRef = useRef<PlannedFlight[]>([]);

  function sync() {
    setTime(engine.current.time());
    setFlights(engine.current.flights());
    setStats(engine.current.stats());
  }

  function applyPlanning(plans: PlannedFlight[]) {
    if (plans.length) {
      engine.current.loadSchedule(
        plans.map((plan) => ({
          scheduled_minute: plan.scheduled_minute,
          duration_minutes: plan.duration_minutes,
        }))
      );
    }
  }

  function reset(s = strategy, d = delay, b = breakdown) {
    setRunning(false);
    engine.current.reset(s, d, b, 42);
    applyPlanning(planningRef.current);
    sync();
    setComparison(null);
  }

  function updatePlanning(next: PlannedFlight[]) {
    planningRef.current = next;
    setPlanning(next);
    setRunning(false);
    engine.current.reset(strategy, delay, breakdown, 42);
    applyPlanning(next);
    sync();
    setComparison(null);
  }

  useEffect(() => {
    let live = true;
    createSimulator().then(({ sim, mode: simulationMode }) => {
      if (!live) return;
      engine.current = sim;
      setMode(simulationMode);
      sim.reset(1, 30, false, 42);
      if (planningRef.current.length) {
        sim.loadSchedule(
          planningRef.current.map((plan) => ({
            scheduled_minute: plan.scheduled_minute,
            duration_minutes: plan.duration_minutes,
          }))
        );
      }
      setTime(sim.time());
      setFlights(sim.flights());
      setStats(sim.stats());
    });
    return () => { live = false; };
  }, []);

  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => {
      engine.current.step(speed);
      sync();
      if (
        engine.current.time() >=
        Math.max(200, ...planningRef.current.map(
          (plan) => plan.scheduled_minute + plan.duration_minutes + delay + 180
        ))
      ) {
        setRunning(false);
      }
    }, 250);
    return () => clearInterval(interval);
  }, [running, speed, delay]);

  async function refresh() {
    setScenariosLoading(true);
    setScenariosError('');
    try {
      const response = await fetch(`${API}/api/scenarios`);
      if (!response.ok) throw new Error('Chargement impossible');
      setScenarios(await response.json());
    } catch {
      setScenariosError('Impossible de charger vos scénarios pour le moment. Veuillez réessayer.');
    } finally {
      setScenariosLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function save() {
    try {
      const response = await fetch(`${API}/api/scenarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description: 'AirportOps interactive simulation',
          delay,
          breakdown,
          seed: 42,
        }),
      });
      if (!response.ok) throw new Error('Enregistrement impossible');
      const scenario: Scenario = await response.json();
      setScenarioId(scenario.id);

      const runResponse = await fetch(`${API}/api/scenarios/${scenario.id}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy: strategy ? 'optimized' : 'baseline',
          ...stats,
          flights,
        }),
      });
      if (!runResponse.ok) throw new Error('Enregistrement des résultats impossible');

      setNotice('Scénario et résultats enregistrés.');
      await refresh();
    } catch {
      setNotice('Impossible d’enregistrer tous les résultats pour le moment. Veuillez réessayer.');
    }
  }

  function exportReport() {
    const report = {
      planning,
      product: 'AirportOps',
      generated: new Date().toISOString(),
      scenario: { name, delay, breakdown, strategy },
      engine: mode,
      stats,
      flights,
      comparison,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'airportops-report.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  async function removeScenario(id: string) {
    if (removingScenarioId !== null) return;
    if (!window.confirm('Supprimer ce scénario et ses exécutions ?')) return;

    setRemovingScenarioId(id);
    try {
      const response = await fetch(`${API}/api/scenarios/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Suppression impossible');
      if (scenarioId === id) setScenarioId('');
      setNotice('Scénario supprimé.');
      await refresh();
    } catch {
      setNotice('Impossible de supprimer ce scénario pour le moment. Veuillez réessayer.');
    } finally {
      setRemovingScenarioId(null);
    }
  }

  function compare() {
    setRunning(false);
    function one(s: number) {
      engine.current.reset(s, delay, breakdown, 42);
      applyPlanning(planningRef.current);
      engine.current.step(1600);
      return engine.current.stats();
    }

    const baseline = one(0);
    const optimized = one(1);
    setComparison({ baseline, optimized });
    engine.current.reset(strategy, delay, breakdown, 42);
    applyPlanning(planningRef.current);
    sync();
  }

  function load(s: Scenario) {
    setScenarioId(s.id);
    setName(s.name);
    setDelay(s.delay);
    setBreakdown(s.breakdown);
    reset(strategy, s.delay, s.breakdown);
    setNotice(`Scénario « ${s.name} » chargé.`);
  }

  const statCards = [
    { icon: <Plane />, label: 'Vols traités', value: `${stats.finished} / ${planning.length || 10}`, detail: 'Trafic simulé' },
    { icon: <Clock3 />, label: 'Retard cumulé', value: `${stats.total_delay} min`, detail: 'Sur les vols traités' },
    { icon: <AlertTriangle />, label: 'Conflits détectés', value: stats.conflicts, detail: 'Conflits de portes' },
    { icon: <Truck />, label: 'Missions réalisées', value: stats.vehicle_missions, detail: 'Véhicules au sol' },
  ];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo"><Plane size={23} /></div>
          <div>
            <strong>Airport<span>Ops</span></strong>
            <small>OPERATIONS SIMULATOR</small>
          </div>
        </div>

        <div className="nav-caption">WORKSPACE</div>
        <div className="navitem active">
          <Activity size={18} /> Simulation <ChevronRight size={16} className="push" />
        </div>
        <div className="navitem"><CalendarClock size={18} /> Scénarios</div>
        <div className="navitem"><GitCompareArrows size={18} /> Comparaison</div>
        <div className="nav-caption">INFRASTRUCTURE</div>
        <div className="navitem"><Plane size={18} /> Avions &amp; Portes</div>
        <div className="navitem"><Truck size={18} /> Ground Support</div>
        <div className="navitem"><Database size={18} /> Historique</div>

        <div className="side-footer">
          <i className="dot green" />
          {running ? 'Simulation en cours' : 'Simulation prête'}
          <small>AirportOps • Planning des vols</small>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="breadcrumbs">WORKSPACE <ChevronRight size={13} /> SIMULATEUR</div>
            <h1>Airport Operations <span>Control</span></h1>
            <p>Supervisez les vols, simulez des incidents et comparez les stratégies.</p>
          </div>
          <div className="top-right">
            <span className="status"><i className="dot green" /> ENVIRONNEMENT DÉMO</span>
            <div className="avatar">AO</div>
          </div>
        </header>

        <div className="stats">
          {statCards.map((card, index) => (
            <div className="stat" key={index}>
              <div className="stat-top">
                <span>{card.label}</span>
                <div className="stat-icon">{card.icon}</div>
              </div>
              <strong>{card.value}</strong>
              <small>{card.detail}</small>
            </div>
          ))}
        </div>

        <div className="content">
          <div className="workspace">
            <div className="section-title">
              <h2>Vue opérationnelle</h2>
              <div className="clock">HEURE SIMULÉE <b>{formatTime(time)}</b></div>
            </div>

            <AirportMap flights={flights} time={time} />

            <div className="controls">
              <div className="buttons">
                <button className="primary" onClick={() => setRunning(!running)}>
                  {running ? <Pause size={17} /> : <Play size={17} />}
                  {running ? 'Pause' : 'Démarrer'}
                </button>
                <button onClick={() => reset()}>
                  <RotateCcw size={16} /> Réinitialiser
                </button>
                <button onClick={() => { engine.current.step(1); sync(); }}>
                  +1 min
                </button>
              </div>
              <div className="speed">
                Vitesse
                <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                  <option value="1">×1</option>
                  <option value="2">×2</option>
                  <option value="5">×5</option>
                  <option value="10">×10</option>
                  <option value="20">×20</option>
                </select>
              </div>
            </div>

            <div className="table-card">
              <div className="section-title">
                <h2>Tableau des vols</h2>
                <span className="minor">{planning.length || 10} vols programmés</span>
              </div>
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>VOL</th>
                      <th>ARRIVÉE</th>
                      <th>PORTE</th>
                      <th>DÉPART</th>
                      <th>RETARD</th>
                      <th>STATUT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flights.map((flight) => (
                      <tr key={flight.id}>
                        <td>
                          <b>{planning[flight.id]?.flight_number ?? `AO${String(1000 + flight.id)}`}</b>
                          <small>{planning[flight.id]?.airline ?? 'AirportOps Airlines'}</small>
                        </td>
                        <td>{formatTime(flight.arrival)}</td>
                        <td>{flight.gate < 0 ? '—' : `G${String(flight.gate + 1).padStart(2, '0')}`}</td>
                        <td>{formatTime(flight.departure)}</td>
                        <td className={flight.delay > 0 ? 'warn' : ''}>
                          {flight.completed ? `+${flight.delay} min` : '—'}
                        </td>
                        <td>
                          <span className={flight.completed ? 'pill success' : 'pill'}>
                            {flight.completed ? 'Affecté' : 'Prévu'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <FlightPlanner plans={planning} onChange={updatePlanning} />
          </div>

          <aside className="panel">
            <div className="panel-block">
              <div className="section-title">
                <h2>Configuration</h2>
                <span className="mini-tag">EN DIRECT</span>
              </div>

              <label>
                Nom du scénario
                <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
              </label>

              <label>
                Stratégie d'affectation
                <select
                  value={strategy}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setStrategy(next);
                    reset(next);
                  }}
                >
                  <option value={0}>Première porte disponible</option>
                  <option value={1}>Portes optimisées</option>
                </select>
              </label>

              <label className="range-label">
                Retard du vol {planning[2]?.flight_number ?? 'AO1002'}
                <b>+{delay} min</b>
              </label>
              <input
                type="range"
                min="0"
                max="90"
                step="5"
                value={delay}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setDelay(next);
                  reset(strategy, next);
                }}
              />
              <div className="range-ends"><span>0 min</span><span>90 min</span></div>

              <label className="check">
                <input
                  type="checkbox"
                  checked={breakdown}
                  onChange={(e) => {
                    setBreakdown(e.target.checked);
                    reset(strategy, delay, e.target.checked);
                  }}
                />
                Panne du véhicule #1
              </label>

              <button className="full" onClick={compare}>
                <GitCompareArrows size={17} /> Comparer les stratégies
              </button>
              <button className="full save" onClick={() => void save()}>
                <Save size={16} /> Sauvegarder le scénario
              </button>
              <button className="full" onClick={exportReport}>
                <Download size={16} /> Exporter les résultats
              </button>
            </div>

            <div className="panel-block">
              <div className="section-title"><h2>Comparaison</h2></div>
              {comparison ? (
                <div className="compare">
                  <div>
                    <span>Stratégie standard</span>
                    <b>{comparison.baseline.total_delay} min</b>
                  </div>
                  <div>
                    <span>Stratégie optimisée</span>
                    <b>{comparison.optimized.total_delay} min</b>
                  </div>
                  <div className="gain">
                    Gain : {comparison.baseline.total_delay - comparison.optimized.total_delay} min
                  </div>
                  <div>
                    <span>Distance véhicules (standard / optimisée)</span>
                    <b>
                      {comparison.baseline.vehicle_distance ?? 0} / {comparison.optimized.vehicle_distance ?? 0} m
                    </b>
                  </div>
                </div>
              ) : (
                <p className="empty">
                  Cliquez sur « Comparer les stratégies » pour lancer deux simulations sur les mêmes données.
                </p>
              )}
            </div>

            <div className="panel-block">
              <div className="section-title">
                <h2>Scénarios sauvegardés</h2>
                <button className="iconbtn" onClick={() => void refresh()} aria-label="Actualiser les scénarios">
                  <RotateCcw size={15} />
                </button>
              </div>

              {scenariosLoading ? (
                <p className="empty">Chargement des scénarios…</p>
              ) : scenariosError ? (
                <p className="planner-error" role="alert">{scenariosError}</p>
              ) : scenarios.length ? (
                scenarios.slice(0, 6).map((scenario) => (
                  <div className="scenario-row" key={scenario.id}>
                    <button
                      className={'scenario ' + (scenarioId === scenario.id ? 'selected' : '')}
                      onClick={() => load(scenario)}
                    >
                      <span>
                        {scenario.name}
                        <small>Retard +{scenario.delay} min {scenario.breakdown ? '• panne' : ''}</small>
                      </span>
                      <ChevronRight size={15} />
                    </button>
                    <button
                      className="delete-scenario"
                      type="button"
                      title={`Supprimer ${scenario.name}`}
                      aria-label={`Supprimer le scénario ${scenario.name}`}
                      disabled={removingScenarioId !== null}
                      onClick={() => void removeScenario(scenario.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              ) : (
                <p className="empty">
                  Aucun scénario enregistré pour le moment. Créez votre première simulation, puis enregistrez-la ici.
                </p>
              )}
            </div>

            {notice && <div className="notice" role="status">{notice}</div>}
          </aside>
        </div>

        <footer>AirportOps © 2026 — Simulation pédagogique · Données fictives</footer>
      </main>
    </div>
  );
}
