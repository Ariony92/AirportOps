export type Flight={id:number,gate:number,scheduled:number,arrival:number,departure:number,delay:number,completed:boolean;vehicle?:number;service_start?:number};
export type Stats={finished:number,total_delay:number,conflicts:number,vehicle_missions:number;vehicle_distance?:number;max_delay?:number};
export interface Simulator {reset(strategy:number,delay:number,breakdown:boolean,seed:number):void;step(minutes:number):void;time():number;flights():Flight[];stats():Stats}
// Identical deterministic event model fallback for development without Emscripten.
const ROADS:[number,number,number][]=[[0,8,80],[1,8,65],[2,9,75],[8,9,100],[9,10,95],[8,3,70],[8,4,100],[9,5,80],[9,6,110],[10,7,75],[3,4,85],[4,5,95],[5,6,90],[6,7,85]];
export function shortestPath(a:number,b:number):number {
 const ds=Array(11).fill(Infinity);const visited=new Set<number>();ds[a]=0;
 for(let n=0;n<11;n++){let u=-1;for(let j=0;j<11;j++)if(!visited.has(j)&&(u<0||ds[j]<ds[u]))u=j;if(u<0||!Number.isFinite(ds[u]))break;if(u===b)return ds[u];visited.add(u);for(const [x,y,w] of ROADS){const v=x===u?y:y===u?x:-1;if(v>=0)ds[v]=Math.min(ds[v],ds[u]+w)}}return -1;
}
export class DemoSimulator implements Simulator {
 private tick=0;private list:Flight[]=[];private cursor=0;private gates:number[]=[];private vehicles:{node:number,free:number,broken:boolean}[]=[];private strategy=1;private metrics:Stats={finished:0,total_delay:0,conflicts:0,vehicle_missions:0,vehicle_distance:0,max_delay:0};
 reset(strategy:number,delay:number,breakdown:boolean,_seed:number){this.tick=0;this.cursor=0;this.strategy=strategy;this.gates=Array(5).fill(0);this.vehicles=[0,1,2].map(i=>({node:i,free:0,broken:breakdown&&i===0}));this.metrics={finished:0,total_delay:0,conflicts:0,vehicle_missions:0,vehicle_distance:0,max_delay:0};this.list=Array.from({length:10},(_,id)=>({id,gate:-1,scheduled:10+id*12,arrival:10+id*12+(id===2?delay:0),departure:-1,delay:0,completed:false,vehicle:-1,service_start:-1})).sort((a,b)=>a.arrival-b.arrival||a.id-b.id);}
 step(minutes:number){const target=this.tick+Math.max(0,minutes);while(this.cursor<this.list.length&&this.list[this.cursor].arrival<=target){const f=this.list[this.cursor++];this.tick=f.arrival;let best={gate:-1,v:-1,start:Infinity,finish:Infinity,dist:Infinity};for(let g=0;g<5;g++){if(this.strategy===0&&g>0)break;for(let v=0;v<3;v++){const veh=this.vehicles[v];if(veh.broken)continue;const dist=shortestPath(veh.node,g+3);if(dist<0)continue;const start=Math.max(this.tick,this.gates[g],Math.max(this.tick,veh.free)+Math.ceil(dist/50));const finish=start+18;if(finish<best.finish||(finish===best.finish&&dist<best.dist))best={gate:g,v,start,finish,dist};}}if(best.gate<0){this.metrics.conflicts++;continue;}if(best.start>this.tick+3)this.metrics.conflicts++;f.gate=best.gate;f.vehicle=best.v;f.service_start=best.start;f.departure=best.finish;f.delay=Math.max(0,best.finish-(f.scheduled+18));f.completed=true;this.gates[best.gate]=best.finish+2;this.vehicles[best.v]={...this.vehicles[best.v],node:best.gate+3,free:best.finish};this.metrics.finished++;this.metrics.total_delay+=f.delay;this.metrics.max_delay=Math.max(this.metrics.max_delay||0,f.delay);this.metrics.vehicle_distance=(this.metrics.vehicle_distance||0)+best.dist;this.metrics.vehicle_missions++;}this.tick=target;}
 time(){return this.tick;}flights(){return [...this.list].sort((a,b)=>a.id-b.id).map(f=>({...f}));}stats(){return {...this.metrics};}
}
type WasmFactory=(opts?:object)=>Promise<{_ao_reset:(s:number,d:number,b:number,seed:number)=>void,_ao_step:(m:number)=>void,_ao_time:()=>number,_ao_flight_count:()=>number,_ao_flight:(i:number,f:number)=>number,_ao_stat:(f:number)=>number}>;

export async function createSimulator(): Promise<{
  sim: Simulator;
  mode: string;
}> {
  try {
    const globalWindow = window as Window & {
      AirportOpsModule?: WasmFactory;
    };

    if (!globalWindow.AirportOpsModule) {
      await new Promise<void>((resolve, reject) => {
        const script = document.createElement("script");

        script.src = "/wasm/airportops.js";
        script.onload = () => resolve();
        script.onerror = () =>
          reject(new Error("Impossible de charger WebAssembly"));

        document.head.appendChild(script);
      });
    }

    const factory = globalWindow.AirportOpsModule;

    if (!factory) {
      throw new Error("AirportOpsModule introuvable");
    }

    const wasm = await factory({
      locateFile: (file: string) => `/wasm/${file}`,
    });

    const sim: Simulator = {
      reset: (s, d, b, seed) =>
        wasm._ao_reset(s, d, Number(b), seed),

      step: (m) => wasm._ao_step(m),

      time: () => wasm._ao_time(),

      flights: () =>
        Array.from(
          { length: wasm._ao_flight_count() },
          (_, i) => ({
            id: wasm._ao_flight(i, 0),
            gate: wasm._ao_flight(i, 1),
            scheduled: wasm._ao_flight(i, 2),
            arrival: wasm._ao_flight(i, 3),
            departure: wasm._ao_flight(i, 4),
            delay: wasm._ao_flight(i, 5),
            completed: wasm._ao_flight(i, 6) === 1,
            vehicle: wasm._ao_flight(i, 7),
            service_start: wasm._ao_flight(i, 8),
          })
        ),

      stats: () => ({
        finished: wasm._ao_stat(0),
        total_delay: wasm._ao_stat(1),
        conflicts: wasm._ao_stat(2),
        vehicle_missions: wasm._ao_stat(3),
        vehicle_distance: wasm._ao_stat(4),
        max_delay: wasm._ao_stat(5),
      }),
    };

    return { sim, mode: "C++ / WebAssembly" };
  } catch (error) {
    console.error("Erreur WebAssembly :", error);

    return {
      sim: new DemoSimulator(),
      mode: "TypeScript (secours)",
    };
  }
}
