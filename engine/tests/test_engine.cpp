#include "airportops.h"
#include <cassert>
int main(){
 assert(ao_path(0,3)==150);assert(ao_path(3,0)==150);assert(ao_path(-1,3)==-1);
 ao_reset(1,30,0,42);ao_step(1000);
 assert(ao_stat(0)==10);assert(ao_stat(3)==10);assert(ao_stat(4)>0);assert(ao_vehicle_count()==3);
 int optimized=ao_stat(1);int distance=ao_stat(4);
 for(int i=0;i<10;i++){assert(ao_flight(i,6)==1);assert(ao_flight(i,1)>=0&&ao_flight(i,1)<5);assert(ao_flight(i,7)>=0&&ao_flight(i,7)<3);}
 ao_reset(0,30,0,42);ao_step(1000);assert(ao_stat(0)==10);assert(optimized<=ao_stat(1));
 ao_reset(1,30,0,42);ao_step(1000);assert(optimized==ao_stat(1));assert(distance==ao_stat(4));
 ao_reset(1,30,1,42);ao_step(1000);assert(ao_stat(0)==10);assert(ao_vehicle(0,3)==1);assert(ao_vehicle(0,5)==0);
 ao_reset(1,30,0,42);ao_step(0);assert(ao_stat(0)==0);ao_step(10);assert(ao_stat(0)==1);
 // V0.2: a saved timetable replaces the generated demo flights.
 ao_reset(1,0,0,42);
 ao_schedule_clear();
 assert(ao_flight_count()==0);
 assert(ao_schedule_add(15,30,0)==1);
 assert(ao_schedule_add(80,12,7)==1);
 assert(ao_schedule_add(-1,12,0)==0);
 assert(ao_schedule_add(10,3,0)==0);
 ao_step(30);
 assert(ao_flight_count()==2);
 assert(ao_stat(0)==1);
 assert(ao_flight(0,2)==15 && ao_flight(0,4)>=45);
 ao_step(200);
 assert(ao_stat(0)==2);
 assert(ao_flight(1,3)==87);
 ao_reset(1,0,0,42);
 assert(ao_flight_count()==10); // legacy compatibility
 return 0;
}
