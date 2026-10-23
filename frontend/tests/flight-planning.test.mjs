import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DemoSimulator,shortestPath} from '../src/simulation.ts';

test('V0.1 demo mode remains backward compatible', () => {
  const simulator=new DemoSimulator();
  simulator.reset(1,30,false,42);
  assert.equal(simulator.flights().length,10);
  simulator.step(1600);
  assert.equal(simulator.stats().finished,10);
  assert.equal(shortestPath(0,3),150);
});

test('V0.2 loads a custom three-flight timetable', () => {
  const simulator=new DemoSimulator();
  simulator.reset(1,25,false,42);
  simulator.loadSchedule([
    {scheduled_minute:15,duration_minutes:30},
    {scheduled_minute:80,duration_minutes:12},
    {scheduled_minute:100,duration_minutes:5},
  ]);
  assert.deepEqual(simulator.flights().map(f=>f.scheduled),[15,80,100]);
  assert.equal(simulator.flights()[2].arrival,125);
  simulator.step(17);
  assert.equal(simulator.stats().finished,1);
  simulator.step(1500);
  assert.equal(simulator.stats().finished,3);
});

test('V0.2 rejects invalid or excessive schedules', () => {
  const simulator=new DemoSimulator();
  simulator.reset(1,0,false,42);
  assert.throws(()=>simulator.loadSchedule([{scheduled_minute:-1,duration_minutes:12}]));
  assert.throws(()=>simulator.loadSchedule(Array.from({length:11},()=>({scheduled_minute:15,duration_minutes:12}))));
});

test('V0.2 strategic comparisons use the same flight timetable', () => {
  const plans=[{scheduled_minute:10,duration_minutes:25},{scheduled_minute:20,duration_minutes:30},{scheduled_minute:30,duration_minutes:10}];
  function one(strategy){const sim=new DemoSimulator();sim.reset(strategy,10,false,42);sim.loadSchedule(plans);sim.step(1600);return sim.stats();}
  const baseline=one(0),optimized=one(1);
  assert.equal(baseline.finished,3);
  assert.equal(optimized.finished,3);
  assert.ok(optimized.total_delay<=baseline.total_delay);
});
