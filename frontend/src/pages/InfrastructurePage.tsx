import InfrastructureManager from '../features/operations/InfrastructureManager';
import type { PlannedFlight } from '../features/planning/FlightPlanner';
export default function InfrastructurePage({planning}:{planning:PlannedFlight[]}){
  return <div className="workspace-page"><div className="page-heading"><div><p className="eyebrow">INFRASTRUCTURES</p><h1>Pistes et services au sol</h1><p>Réseau de circulation, moyens matériels et interventions programmées.</p></div></div><InfrastructureManager plans={planning} simulationMinute={1440}/></div>;
}
