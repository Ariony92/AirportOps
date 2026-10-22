#include "airportops.h"
#include <iostream>
int main(int argc,char** argv){int strategy=argc>1?std::stoi(argv[1]):1;int delay=argc>2?std::stoi(argv[2]):30;int breakdown=argc>3?std::stoi(argv[3]):0;
ao_reset(strategy,delay,breakdown,42);ao_step(1000);
std::cout<<"{\"finished\":"<<ao_stat(0)<<",\"total_delay\":"<<ao_stat(1)<<",\"conflicts\":"<<ao_stat(2)<<"}"<<std::endl;}
