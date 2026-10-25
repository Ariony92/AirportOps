import { apiFetch } from '../../shared/api';
import { useEffect, useState, type FormEvent } from 'react';
import { CalendarClock, PenLine, Plus, RotateCcw, Trash2 } from 'lucide-react';
import type { Aircraft } from './AircraftManager';
import { useAviationCatalog } from './hooks/useAviationCatalog';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export type PlannedFlight = {
  id: string;
  flight_number: string;
  airline: string;
  origin: string;
  destination: string;
  scheduled_minute: number;
  duration_minutes: number;
  aircraft_id: string | null;
};

type Draft = Omit<PlannedFlight, 'id'>;

const emptyDraft: Draft = {
  flight_number: 'AO2000',
  airline: 'AirportOps Airlines',
  origin: 'CDG',
  destination: 'AMS',
  scheduled_minute: 15,
  duration_minutes: 18,
  aircraft_id: null,
};

function formatTime(minutes: number): string {
  const t = minutes + 360;
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
}

type FlightPlannerProps = {
  plans: PlannedFlight[];
  onChange: (plans: PlannedFlight[]) => void;
  aircraft: Aircraft[];
};

export default function FlightPlanner({ plans, onChange, aircraft }: FlightPlannerProps) {
  const { airlines } = useAviationCatalog();
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [error, setError] = useState('');
  const [working, setWorking] = useState(false);
  const [connected, setConnected] = useState(false);

  async function refresh() {
    try {
      const response = await apiFetch(`${API}/api/flight-plans`);
      if (!response.ok) {
        throw new Error('Chargement impossible');
      }

      const list = (await response.json()) as PlannedFlight[];
      onChange(list);
      setConnected(true);
      setError('');
    } catch {
      setConnected(false);
      setError('Impossible de charger le planning pour le moment. Réessayez avec le bouton d’actualisation.');
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  function edit(item: PlannedFlight) {
    setEditing(item.id);
    setDraft({
      flight_number: item.flight_number,
      airline: item.airline,
      origin: item.origin,
      destination: item.destination,
      scheduled_minute: item.scheduled_minute,
      duration_minutes: item.duration_minutes,
      aircraft_id: item.aircraft_id,
    });
    setError('');
  }

  function startNew() {
    setEditing(null);
    setDraft(emptyDraft);
    setError('');
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError('');

    try {
      const response = await apiFetch(`${API}/api/flight-plans${editing ? '/' + editing : ''}`, {
        method: editing ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...draft,
          flight_number: draft.flight_number.trim().toUpperCase(),
          origin: draft.origin.trim().toUpperCase(),
          destination: draft.destination.trim().toUpperCase(),
        }),
      });

      if (!response.ok) {
        if (response.status === 409) {
          const info = await response.json().catch(() => null) as { detail?: string } | null;
          const detail = info?.detail ?? '';
          if (detail.includes('overlapping')) {
            throw new Error('Cet avion est déjà affecté à un autre vol sur ce créneau.');
          }
          throw new Error('Ce numéro de vol est déjà utilisé ou le planning a atteint 10 vols.');
        }
        if (response.status === 404) {
          throw new Error('Ce vol n’est plus disponible. Actualisez le planning.');
        }
        if (response.status === 422) {
          throw new Error('Vérifiez les informations saisies avant de continuer.');
        }
        throw new Error('Impossible d’enregistrer le vol pour le moment.');
      }

      await refresh();
      startNew();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible d’enregistrer ce vol pour le moment.');
    } finally {
      setWorking(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm('Supprimer ce vol du planning ?')) return;

    setWorking(true);
    setError('');

    try {
      const response = await apiFetch(`${API}/api/flight-plans/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Impossible de supprimer ce vol pour le moment.');
      }

      await refresh();
      startNew();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de supprimer ce vol pour le moment.');
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="table-card flight-planner" aria-label="Planning des vols" id="planning">
      <div className="section-title">
        <h2>
          <CalendarClock size={18} />
          Planning des vols
          <span className="minor">{plans.length}/10 personnalisés</span>
        </h2>
        <button type="button" onClick={() => void refresh()} aria-label="Actualiser le planning">
          <RotateCcw size={14} />
        </button>
      </div>

      <p className="planner-intro">
        Personnalisez jusqu’à 10 vols. Les horaires sont calculés à partir de 06:00.
        Le retard configurable s’applique au troisième vol.
      </p>

      {error && <p className="planner-error" role="status">{error}</p>}

      {plans.length > 0 && (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>VOL</th>
                <th>TRAJET</th>
                <th>PROGRAMMÉ</th>
                <th>SERVICE</th>
                <th>AVION</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.flight_number}</b>
                    <small>{item.airline}</small>
                  </td>
                  <td>{item.origin} → {item.destination}</td>
                  <td>{formatTime(item.scheduled_minute)}</td>
                  <td>{item.duration_minutes} min</td>
                  <td>{aircraft.find(a => a.id === item.aircraft_id)?.registration ?? 'Non attribué'}</td>
                  <td className="planner-actions">
                    <button type="button" title="Modifier" onClick={() => edit(item)}>
                      <PenLine size={15} />
                    </button>
                    <button type="button" title="Supprimer" onClick={() => void remove(item.id)} disabled={working}>
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className="planner-form" onSubmit={(e) => void save(e)}>
        <label>
          N° de vol
          <input
            required
            maxLength={12}
            minLength={3}
            pattern="[a-zA-Z0-9-]+"
            value={draft.flight_number}
            onChange={(e) => setDraft({ ...draft, flight_number: e.target.value })}
          />
        </label>
        <label>
          Compagnie
          <input
            required
            maxLength={80}
            list="flight-airlines"
            value={draft.airline}
            onChange={(e) => setDraft({ ...draft, airline: e.target.value })}
          />
        </label>
        <datalist id="flight-airlines">{airlines.map(a => <option key={a} value={a} />)}</datalist>
        <label>
          Départ (IATA)
          <input
            required
            maxLength={3}
            minLength={3}
            pattern="[a-zA-Z]{3}"
            value={draft.origin}
            onChange={(e) => setDraft({ ...draft, origin: e.target.value })}
          />
        </label>
        <label>
          Arrivée (IATA)
          <input
            required
            maxLength={3}
            minLength={3}
            pattern="[a-zA-Z]{3}"
            value={draft.destination}
            onChange={(e) => setDraft({ ...draft, destination: e.target.value })}
          />
        </label>
        <label>
          Minutes après 06:00
          <input
            type="number"
            min={0}
            max={1200}
            required
            value={draft.scheduled_minute}
            onChange={(e) => setDraft({ ...draft, scheduled_minute: Number(e.target.value) })}
          />
        </label>
        <label>
          Service (minutes)
          <input
            type="number"
            min={5}
            max={180}
            required
            value={draft.duration_minutes}
            onChange={(e) => setDraft({ ...draft, duration_minutes: Number(e.target.value) })}
          />
        </label>
        <label>Appareil attribué
          <select value={draft.aircraft_id ?? ''} onChange={e => setDraft({
            ...draft, aircraft_id: e.target.value || null
          })}>
            <option value="">Aucun appareil attribué</option>
            {aircraft.map(item => (
              <option value={item.id} key={item.id}>
                {item.registration} — {item.manufacturer} {item.model}
              </option>
            ))}
          </select>
        </label>
        <div className="planner-submit">
          <button
            className="primary"
            type="submit"
            disabled={working || !connected || (!editing && plans.length >= 10)}
          >
            <Plus size={15} />
            {editing ? 'Enregistrer les modifications' : 'Ajouter un vol'}
          </button>
          {editing && (
            <button type="button" onClick={startNew}>Annuler</button>
          )}
        </div>
      </form>

      <p className="planner-intro">
        Les changements sont conservés et appliqués lors de la prochaine simulation.
        L'affectation d'un appareil est informative dans cette version ; ses caractéristiques
        n'influencent pas encore le calcul des déplacements.
      </p>
    </section>
  );
}
