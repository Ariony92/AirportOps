import {useEffect,useState,type FormEvent} from 'react';
import {CalendarClock,PenLine,Plus,RotateCcw,Trash2} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export type PlannedFlight = {
  id: string;
  flight_number: string;
  airline: string;
  origin: string;
  destination: string;
  scheduled_minute: number;
  duration_minutes: number;
};
type Draft = Omit<PlannedFlight,'id'>;
const emptyDraft:Draft={flight_number:'AO2000',airline:'AirportOps Airlines',origin:'CDG',destination:'AMS',scheduled_minute:15,duration_minutes:18};
const fmt = (minutes:number)=>{
  const t=minutes+360;
  return `${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;
};

export default function FlightPlanner({plans,onChange}:{plans:PlannedFlight[],onChange:(plans:PlannedFlight[])=>void}){
  const [editing,setEditing]=useState<string|null>(null);
  const [draft,setDraft]=useState<Draft>(emptyDraft);
  const [error,setError]=useState('');
  const [working,setWorking]=useState(false);
  const [connected,setConnected]=useState(false);
  async function refresh(){
    try {
      const response=await fetch(`${API}/api/flight-plans`);
      if(!response.ok)throw Error('API indisponible');
      const list=await response.json() as PlannedFlight[];
      onChange(list);setConnected(true);setError('');
    }catch{setConnected(false);setError('Le backend est indisponible. La simulation utilise les 10 vols de démonstration.');}
  }
  useEffect(()=>{void refresh()},[]);
  function edit(item:PlannedFlight){
    setEditing(item.id);
    setDraft({flight_number:item.flight_number,airline:item.airline,origin:item.origin,destination:item.destination,scheduled_minute:item.scheduled_minute,duration_minutes:item.duration_minutes});
    setError('');
  }
  function startNew(){setEditing(null);setDraft(emptyDraft);setError('');}
  async function save(event:FormEvent<HTMLFormElement>){
    event.preventDefault();setWorking(true);setError('');
    try{
      const response=await fetch(`${API}/api/flight-plans${editing?'/'+editing:''}`,{
        method:editing?'PATCH':'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({...draft,flight_number:draft.flight_number.trim().toUpperCase(),origin:draft.origin.trim().toUpperCase(),destination:draft.destination.trim().toUpperCase()})
      });
      if(!response.ok){
        const payload=await response.json().catch(()=>null) as {detail?:unknown}|null;
        throw Error(typeof payload?.detail==='string'?payload.detail:`Erreur HTTP ${response.status}`);
      }
      await refresh();startNew();
    }catch(e){setError(e instanceof Error?e.message:'Impossible de sauvegarder le vol');}
    finally{setWorking(false);}
  }
  async function remove(id:string){
    if(!window.confirm('Supprimer ce vol du planning ?'))return;
    setWorking(true);setError('');
    try{
      const response=await fetch(`${API}/api/flight-plans/${id}`,{method:'DELETE'});
      if(!response.ok)throw Error(`Erreur HTTP ${response.status}`);
      await refresh();startNew();
    }catch(e){setError(e instanceof Error?e.message:'Suppression impossible');}
    finally{setWorking(false);}
  }
  return <section className="table-card flight-planner" aria-label="Planning des vols">
    <div className="section-title"><h2><CalendarClock size={18}/> Planning des vols <span className="minor">{plans.length}/10 personnalisés</span></h2><button onClick={()=>void refresh()} aria-label="Actualiser le planning"><RotateCcw size={14}/></button></div>
    <p className="planner-intro">Les vols enregistrés remplacent les 10 vols de démonstration. Les horaires sont exprimés à partir de 06:00. Le retard configurable affecte le troisième vol.</p>
    {error&&<p className="planner-error" role="status">{error}</p>}
    {plans.length>0&&<div className="tablewrap"><table><thead><tr><th>VOL</th><th>TRAJET</th><th>PROGRAMMÉ</th><th>SERVICE</th><th>ACTIONS</th></tr></thead><tbody>{plans.map(item=><tr key={item.id}><td><b>{item.flight_number}</b><small>{item.airline}</small></td><td>{item.origin} → {item.destination}</td><td>{fmt(item.scheduled_minute)}</td><td>{item.duration_minutes} min</td><td className="planner-actions"><button type="button" title="Modifier" onClick={()=>edit(item)}><PenLine size={15}/></button><button type="button" title="Supprimer" onClick={()=>void remove(item.id)} disabled={working}><Trash2 size={15}/></button></td></tr>)}</tbody></table></div>}
    <form className="planner-form" onSubmit={e=>void save(e)}>
      <label>N° de vol<input required maxLength={12} minLength={3} pattern="[a-zA-Z0-9-]+" value={draft.flight_number} onChange={e=>setDraft({...draft,flight_number:e.target.value})}/></label>
      <label>Compagnie<input required maxLength={80} value={draft.airline} onChange={e=>setDraft({...draft,airline:e.target.value})}/></label>
      <label>Départ (IATA)<input required maxLength={3} minLength={3} pattern="[a-zA-Z]{3}" value={draft.origin} onChange={e=>setDraft({...draft,origin:e.target.value})}/></label>
      <label>Arrivée (IATA)<input required maxLength={3} minLength={3} pattern="[a-zA-Z]{3}" value={draft.destination} onChange={e=>setDraft({...draft,destination:e.target.value})}/></label>
      <label>Minutes après 06:00<input type="number" min={0} max={1200} required value={draft.scheduled_minute} onChange={e=>setDraft({...draft,scheduled_minute:Number(e.target.value)})}/></label>
      <label>Service (minutes)<input type="number" min={5} max={180} required value={draft.duration_minutes} onChange={e=>setDraft({...draft,duration_minutes:Number(e.target.value)})}/></label>
      <div className="planner-submit"><button className="primary" disabled={working||!connected||(!editing&&plans.length>=10)} type="submit"><Plus size={15}/>{editing?'Enregistrer les modifications':'Ajouter un vol'}</button>{editing&&<button type="button" onClick={startNew}>Annuler</button>}</div>
    </form>
    <p className="planner-intro">Cette V0.2 conserve le planning dans la base globale. L'association d'un planning figé à chaque scénario sera une évolution ultérieure.</p>
  </section>;
}
