import FlightPlanner, { type PlannedFlight } from '../features/planning/FlightPlanner';
import AircraftManager, { type Aircraft } from '../features/planning/AircraftManager';
export default function PlanningPage({planning,onPlanning,aircraft,onAircraft}:{planning:PlannedFlight[];onPlanning:(list:PlannedFlight[])=>void;aircraft:Aircraft[];onAircraft:(list:Aircraft[])=>void}){
  return <div className="workspace-page"><div className="page-heading"><div><p className="eyebrow">PLANIFICATION</p><h1>Vols et flotte aérienne</h1><p>Une seule vue pour le planning et l’affectation des appareils.</p></div></div>
    <FlightPlanner plans={planning} onChange={onPlanning} aircraft={aircraft}/>
    <AircraftManager aircraft={aircraft} onChange={onAircraft}/>
  </div>;
}
