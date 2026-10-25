import { useEffect, useState } from 'react';
import { Activity, CalendarDays, CircleAlert, Gauge, Layers, Plane } from 'lucide-react';
import { apiGet } from './shared/api';
import type { PlannedFlight } from './features/planning/FlightPlanner';
import type { Aircraft } from './features/planning/AircraftManager';
import SimulationPage from './pages/SimulationPage';
import PlanningPage from './pages/PlanningPage';
import InfrastructurePage from './pages/InfrastructurePage';
import IncidentsPage from './pages/IncidentsPage';
import ScenariosPage from './pages/ScenariosPage';

type Page = 'simulation' | 'planning' | 'infrastructures' | 'incidents' | 'scenarios';
const pages: {id:Page;label:string;description:string;icon:typeof Activity}[] = [
  {id:'simulation',label:'Simulation',description:'Carte et chronologie',icon:Activity},
  {id:'planning',label:'Vols & flotte',description:'Planning et appareils',icon:CalendarDays},
  {id:'infrastructures',label:'Infrastructures',description:'Pistes et véhicules',icon:Layers},
  {id:'incidents',label:'Incidents & KPI',description:'Perturbations et analyses',icon:CircleAlert},
  {id:'scenarios',label:'Scénarios',description:'Historique des calculs',icon:Gauge},
];
function pageFromHash():Page {const value=window.location.hash.replace('#/','');return pages.find(p=>p.id===value)?.id??'simulation';}

export default function App(){
  const [page,setPage]=useState<Page>(pageFromHash);
  const [planning,setPlanning]=useState<PlannedFlight[]>([]);const [aircraft,setAircraft]=useState<Aircraft[]>([]);
  useEffect(()=>{const listener=()=>setPage(pageFromHash());window.addEventListener('hashchange',listener);return()=>window.removeEventListener('hashchange',listener);},[]);
  useEffect(()=>{void Promise.all([apiGet<PlannedFlight[]>('/api/flight-plans'),apiGet<Aircraft[]>('/api/aircraft')]).then(([plans, fleet])=>{setPlanning(plans);setAircraft(fleet);}).catch(()=>{});},[]);
  return <div className="shell app-shell"><aside className="sidebar">
    <div className="brand"><div className="brand-logo"><Plane size={22}/></div><div><strong>Airport<span>Ops</span></strong><small>OPERATIONS CONTROL</small></div></div>
    <p className="nav-caption">NAVIGATION</p>
    <nav aria-label="Navigation principale">{pages.map(item=>{const Icon=item.icon;return <a key={item.id} href={`#/${item.id}`} className={`navitem ${page===item.id?'active':''}`} aria-current={page===item.id?'page':undefined}><Icon size={19}/><span>{item.label}<small>{item.description}</small></span></a>;})}</nav>
    <div className="side-footer"><i className="dot green"/>Prévision côté serveur<small>AirportOps • v0.9.0</small></div>
  </aside><main className="main app-main"><header className="app-topbar"><div className="breadcrumbs"><span>AirportOps</span><span>/</span><b>{pages.find(p=>p.id===page)?.label}</b></div><span className="version-chip">PROTOTYPE V0.9.0</span></header>
    {page==='simulation'&&<SimulationPage/>}
    {page==='planning'&&<PlanningPage planning={planning} onPlanning={setPlanning} aircraft={aircraft} onAircraft={setAircraft}/>}
    {page==='infrastructures'&&<InfrastructurePage planning={planning}/>}
    {page==='incidents'&&<IncidentsPage planning={planning}/>}
    {page==='scenarios'&&<ScenariosPage/>}
  </main></div>;
}
