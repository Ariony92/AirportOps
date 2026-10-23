import { useEffect, useState, type FormEvent } from 'react';
import { Plane, PenLine, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useAviationCatalog } from './hooks/useAviationCatalog';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export type Aircraft = {
  id: string;
  registration: string;
  airline: string;
  manufacturer: string;
  model: string;
  category: 'regional' | 'narrow_body' | 'wide_body';
  seats: number;
};

type AircraftDraft = Omit<Aircraft, 'id'>;

const emptyDraft: AircraftDraft = {
  registration: '',
  airline: 'AirportOps Airlines',
  manufacturer: 'Airbus',
  model: 'A320neo',
  category: 'narrow_body',
  seats: 180
};

const categoryLabels: Record<Aircraft['category'], string> = {
  regional: 'Régional',
  narrow_body: 'Moyen-courrier',
  wide_body: 'Long-courrier'
};

type Props = {
  aircraft: Aircraft[];
  onChange: (items: Aircraft[]) => void;
};

export default function AircraftManager({ aircraft, onChange }: Props) {
  const { airlines, models } = useAviationCatalog();
  const [draft, setDraft] = useState<AircraftDraft>(emptyDraft);
  const [editing, setEditing] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function refresh() {
    try {
      const response = await fetch(`${API}/api/aircraft`);
      if (!response.ok) throw new Error('Impossible de charger les appareils.');
      onChange((await response.json()) as Aircraft[]);
      setError('');
    } catch {
      setError('Impossible de charger la flotte. Réessayez avec le bouton d’actualisation.');
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  function edit(item: Aircraft) {
    setEditing(item.id);
    setDraft({
      registration: item.registration,
      airline: item.airline,
      manufacturer: item.manufacturer,
      model: item.model,
      category: item.category,
      seats: item.seats
    });
    setError('');
    setMessage('');
  }

  function resetForm() {
    setEditing(null);
    setDraft(emptyDraft);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API}/api/aircraft${editing ? '/' + editing : ''}`, {
        method: editing ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...draft,
          registration: draft.registration.trim().toUpperCase(),
          airline: draft.airline.trim(),
          manufacturer: draft.manufacturer.trim(),
          model: draft.model.trim()
        })
      });
      if (!response.ok) {
        if (response.status === 409) throw new Error('Cette immatriculation est déjà utilisée.');
        if (response.status === 422) throw new Error('Vérifiez les caractéristiques de l’appareil.');
        throw new Error('Impossible d’enregistrer cet appareil.');
      }
      resetForm();
      await refresh();
      setMessage(editing ? 'Appareil mis à jour.' : 'Appareil ajouté à la flotte.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Enregistrement impossible.');
    } finally {
      setWorking(false);
    }
  }

  async function remove(item: Aircraft) {
    if (!window.confirm(`Supprimer l’appareil ${item.registration} ?`)) return;
    setWorking(true);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API}/api/aircraft/${item.id}`, { method: 'DELETE' });
      if (response.status === 409) {
        throw new Error('Cet appareil est attribué à un vol. Retirez son affectation avant de le supprimer.');
      }
      if (!response.ok) throw new Error('Impossible de supprimer cet appareil.');
      if (editing === item.id) resetForm();
      await refresh();
      setMessage('Appareil supprimé.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Suppression impossible.');
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="table-card aircraft-manager" aria-label="Gestion de la flotte" id="flotte">
      <div className="section-title">
        <h2><Plane size={18} /> Flotte aérienne <span className="minor">{aircraft.length} appareil(s)</span></h2>
        <button type="button" onClick={() => void refresh()} aria-label="Actualiser la flotte">
          <RotateCcw size={14} />
        </button>
      </div>
      <p className="planner-intro">
        Enregistrez vos avions puis affectez-les à des vols dans le planning.
        Un appareil ne peut pas assurer deux vols dont les créneaux se chevauchent.
      </p>

      {error && <p className="planner-error" role="alert">{error}</p>}
      {message && <p className="planner-success" role="status">{message}</p>}

      {aircraft.length > 0 ? (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>IMMATRICULATION</th><th>COMPAGNIE</th><th>APPAREIL</th>
                <th>CATÉGORIE</th><th>SIÈGES</th><th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {aircraft.map(item => (
                <tr key={item.id}>
                  <td><b>{item.registration}</b></td>
                  <td>{item.airline}</td>
                  <td>{item.manufacturer} {item.model}</td>
                  <td>{categoryLabels[item.category]}</td>
                  <td>{item.seats}</td>
                  <td className="planner-actions">
                    <button type="button" onClick={() => edit(item)} title="Modifier l’appareil" disabled={working}>
                      <PenLine size={15} />
                    </button>
                    <button type="button" onClick={() => void remove(item)} title="Supprimer l’appareil" disabled={working}>
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty">Aucun appareil enregistré pour le moment. Ajoutez un premier avion ci-dessous.</p>
      )}

      <p className="planner-intro">Modèles civils et compagnies recommandées : choisissez une suggestion ou saisissez librement une autre valeur.</p>
      <form className="planner-form" onSubmit={e => void save(e)}>
        <label>Immatriculation
          <input required minLength={3} maxLength={12} pattern="[a-zA-Z0-9-]+"
            placeholder="F-AO01" value={draft.registration}
            onChange={e => setDraft({ ...draft, registration: e.target.value })} />
        </label>
        <label>Compagnie
          <input required maxLength={80} list="aircraft-airlines" value={draft.airline}
            onChange={e => setDraft({ ...draft, airline: e.target.value })} />
          <datalist id="aircraft-airlines">{airlines.map(a => <option key={a} value={a} />)}</datalist>
        </label>
        <label>Constructeur
          <input required maxLength={80} value={draft.manufacturer}
            onChange={e => setDraft({ ...draft, manufacturer: e.target.value })} />
        </label>
        <label>Modèle
          <input required maxLength={80} list="aircraft-models" value={draft.model}
            onChange={e => {
              const model = models.find(m => m.model.toLowerCase() === e.target.value.toLowerCase());
              setDraft({ ...draft, model: e.target.value,
                manufacturer: model?.manufacturer ?? draft.manufacturer,
                category: model?.category ?? draft.category });
            }} />
          <datalist id="aircraft-models">{models.map((m, i) =>
            <option key={`${m.manufacturer}-${m.model}-${i}`} value={m.model} label={`${m.manufacturer} · ${m.category}`} />
          )}</datalist>
        </label>
        <label>Catégorie
          <select value={draft.category} onChange={e => setDraft({
            ...draft, category: e.target.value as Aircraft['category']
          })}>
            <option value="regional">Régional</option>
            <option value="narrow_body">Moyen-courrier</option>
            <option value="wide_body">Long-courrier</option>
          </select>
        </label>
        <label>Nombre de sièges
          <input required type="number" min={1} max={900} value={draft.seats}
            onChange={e => setDraft({ ...draft, seats: Number(e.target.value) })} />
        </label>
        <div className="planner-submit">
          <button className="primary" disabled={working} type="submit">
            <Plus size={15} /> {editing ? 'Enregistrer les modifications' : 'Ajouter un appareil'}
          </button>
          {editing && <button type="button" onClick={resetForm}>Annuler</button>}
        </div>
      </form>
    </section>
  );
}
