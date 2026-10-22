#pragma once
#include <cstdint>
#include <queue>
#include <vector>
#include <string>
namespace airportops {
struct Flight { int id; int gate; int scheduled; int duration; int arrival; int departure; int delay; bool completed=false; int vehicle=-1; int service_start=-1; };
struct Vehicle { int id; int node; int free_at=0; bool broken=false; int distance=0; int missions=0; };
struct Event { int time; int order; int flight; bool operator<(Event const& b) const {return time==b.time ? order>b.order : time>b.time;} };
struct Stats { int finished=0; int total_delay=0; int conflicts=0; int vehicle_missions=0; int vehicle_distance=0; int max_delay=0; };
class Engine {
 int clock_=0,policy_=0,seq_=0,gate_free_[5]{};
 std::priority_queue<Event> queue_;
 std::vector<Flight> flights_;
 std::vector<Vehicle> vehicles_;
 Stats stats_;
 void process(Event const& e);
 int distance(int start,int dest) const;
public:
 void reset(int policy,int delay,int breakdown,uint32_t seed);
 void step(int minutes);
 int time() const{return clock_;}
 Stats stats() const{return stats_;}
 int flights_count() const{return (int)flights_.size();}
 Flight flight(int index) const{return flights_.at(index);}
 int vehicle_count() const{return (int)vehicles_.size();}
 Vehicle vehicle(int index) const{return vehicles_.at(index);}
 int path_length(int from,int to) const{return distance(from,to);}
};
}
extern "C" {
 void ao_reset(int strategy,int delay,int breakdown,int seed);
 void ao_step(int minutes);
 int ao_time();
 int ao_flight_count();
 int ao_flight(int index,int field);
 int ao_stat(int field);
 int ao_vehicle_count();
 int ao_vehicle(int index,int field);
 int ao_path(int start,int end);
}
