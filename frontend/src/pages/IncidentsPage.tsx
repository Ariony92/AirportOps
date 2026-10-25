import { useEffect, useState } from 'react';
import { apiGet } from '../shared/api';
import DisruptionsAnalytics from '../features/operations/DisruptionsAnalytics';
import type { PlannedFlight } from '../features/planning/FlightPlanner';
type Resource = {id:string; designation?:string;code?:string;start_node?:number;end_node?:number};
export default function IncidentsPage({planning}:{planning:PlannedFlight[]}){
  const [runways,setRunways]=useState<{id:string;label:string}[]>([]);
  const [taxiways,setTaxiways]=useState<{id:string;start_node:number;end_node:number}[]>([]);
  const [vehicles,setVehicles]=useState<{id:string;code:string}[]>([]);
  const [revision,setRevision]=useState(0);
  useEffect(()=>{ let active=true; Promise.all([
    apiGet<Resource[]>('/api/operations/runways'),apiGet<Resource[]>('/api/operations/taxiways'),apiGet<Resource[]>('/api/operations/vehicles')
  ]).then(([r,t,v])=>{if(active){setRunways(r.map(x=>({id:x.id,label:x.designation??''})));setTaxiways(t.map(x=>({id:x.id,start_node:x.start_node??0,end_node:x.end_node??0})));setVehicles(v.map(x=>({id:x.id,code:x.code??''})));}}).catch(()=>{});return()=>{active=false;};},[]);
  return <div className="workspace-page"><div className="page-heading"><div><p className="eyebrow">ANALYSE OPÉRATIONNELLE</p><h1>Incidents et optimisation</h1><p>Perturbations, comparaison des stratégies et prévisions historisées au même endroit.</p></div></div>
  <DisruptionsAnalytics flights={planning} revision={revision} runways={runways} taxiways={taxiways} vehicles={vehicles} onChanged={async()=>{setRevision(n=>n+1);}}/></div>;
}
