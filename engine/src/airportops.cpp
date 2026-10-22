#include "airportops.h"
#include <algorithm>
#include <array>
#include <limits>
#include <queue>
#include <utility>
using namespace airportops;
namespace { Engine global_engine; constexpr int INF=100000000; }
// An undirected 11-node apron road network: depot nodes 0..2, gate nodes 3..7,
// junctions 8..10. Each edge has a positive distance in abstract metres.
int Engine::distance(int start,int dest) const {
 static const std::array<std::array<int,3>,14> edges={{{0,8,80},{1,8,65},{2,9,75},{8,9,100},{9,10,95},{8,3,70},{8,4,100},{9,5,80},{9,6,110},{10,7,75},{3,4,85},{4,5,95},{5,6,90},{6,7,85}}};
 if(start<0||start>10||dest<0||dest>10)return -1;
 std::array<int,11> dist;dist.fill(INF);dist[start]=0;
 using Node=std::pair<int,int>;std::priority_queue<Node,std::vector<Node>,std::greater<Node>> pq;pq.push({0,start});
 while(!pq.empty()) {auto [d,u]=pq.top();pq.pop();if(d!=dist[u])continue;if(u==dest)return d;
  for(auto [a,b,w]:edges){int v=-1;if(a==u)v=b;else if(b==u)v=a;if(v>=0&&d+w<dist[v]){dist[v]=d+w;pq.push({dist[v],v});}}
 }
 return -1;
}
void Engine::reset(int policy,int delay,int breakdown,uint32_t seed){
 (void)seed;clock_=0;policy_=policy==0?0:1;seq_=0;stats_={};queue_={};flights_.clear();
 vehicles_={{0,0,0,breakdown!=0,0,0},{1,1,0,false,0,0},{2,2,0,false,0,0}};
 std::fill(std::begin(gate_free_),std::end(gate_free_),0);
 for(int i=0;i<10;++i){int scheduled=10+i*12;int arrival=scheduled+(i==2?std::max(0,delay):0);
  flights_.push_back({i,-1,scheduled,18,arrival,-1,0,false,-1,-1});queue_.push({arrival,seq_++,i});
 }
}
void Engine::process(Event const& e){
 Flight &f=flights_[e.flight];if(f.completed)return;
 int best_gate=-1,best_vehicle=-1,best_start=INF,best_finish=INF,best_distance=0;
 for(int g=0;g<5;++g){
  if(policy_==0 && g>0)break;
  int gate_start=std::max(clock_,gate_free_[g]);
  for(int v=0;v<(int)vehicles_.size();++v){
   auto const& veh=vehicles_[v];if(veh.broken)continue;
   int dist=distance(veh.node,g+3);if(dist<0)continue;
   int travel=(dist+49)/50; // 50 metres per simulated minute
   int ready=std::max(clock_,veh.free_at)+travel;
   int start=std::max(gate_start,ready),finish=start+f.duration;
   // baseline: fixed gate G1; optimized: earliest finish, then shortest travel
   if(finish<best_finish||(finish==best_finish&&dist<best_distance)){
    best_gate=g;best_vehicle=v;best_start=start;best_finish=finish;best_distance=dist;
   }
  }
 }
 if(best_gate<0){stats_.conflicts++;return;}
 if(best_start>clock_+3)stats_.conflicts++;
 f.gate=best_gate;f.vehicle=best_vehicle;f.service_start=best_start;f.departure=best_finish;
 f.delay=std::max(0,f.departure-(f.scheduled+f.duration));f.completed=true;
 gate_free_[best_gate]=best_finish+2;
 auto &v=vehicles_[best_vehicle];v.node=best_gate+3;v.free_at=best_finish;v.distance+=best_distance;v.missions++;
 stats_.finished++;stats_.total_delay+=f.delay;stats_.max_delay=std::max(stats_.max_delay,f.delay);
 stats_.vehicle_missions++;stats_.vehicle_distance+=best_distance;
}
void Engine::step(int minutes){int target=clock_+std::max(0,minutes);while(!queue_.empty()&&queue_.top().time<=target){auto e=queue_.top();queue_.pop();clock_=e.time;process(e);}clock_=target;}
extern "C" {
void ao_reset(int strategy,int delay,int breakdown,int seed){global_engine.reset(strategy,delay,breakdown,(uint32_t)seed);}
void ao_step(int minutes){global_engine.step(minutes);}
int ao_time(){return global_engine.time();}
int ao_flight_count(){return global_engine.flights_count();}
int ao_flight(int i,int field){if(i<0||i>=global_engine.flights_count())return -1;auto f=global_engine.flight(i);switch(field){case 0:return f.id;case 1:return f.gate;case 2:return f.scheduled;case 3:return f.arrival;case 4:return f.departure;case 5:return f.delay;case 6:return f.completed?1:0;case 7:return f.vehicle;case 8:return f.service_start;default:return -1;}}
int ao_stat(int field){auto s=global_engine.stats();switch(field){case 0:return s.finished;case 1:return s.total_delay;case 2:return s.conflicts;case 3:return s.vehicle_missions;case 4:return s.vehicle_distance;case 5:return s.max_delay;default:return -1;}}
int ao_vehicle_count(){return global_engine.vehicle_count();}
int ao_vehicle(int i,int field){if(i<0||i>=global_engine.vehicle_count())return -1;auto v=global_engine.vehicle(i);switch(field){case 0:return v.id;case 1:return v.node;case 2:return v.free_at;case 3:return v.broken?1:0;case 4:return v.distance;case 5:return v.missions;default:return -1;}}
int ao_path(int from,int to){return global_engine.path_length(from,to);}
}
