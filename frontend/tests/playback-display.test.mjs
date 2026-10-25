import test from 'node:test';
import assert from 'node:assert/strict';
import { positionAt } from '../src/features/simulation/display.ts';
const moving = {
  id: 'A', kind: 'vehicle', label: 'BAG-01', visible_from: 0, visible_until: 30,
  keyframes: [
    {minute:0,x:0,y:0,phase:'idle',label:'En attente'},
    {minute:10,x:0,y:0,phase:'dispatch',label:'Départ'},
    {minute:14,x:100,y:40,phase:'service_start',label:'Au poste'},
    {minute:25,x:100,y:40,phase:'service_end',label:'Terminé'},
  ]
};
test('vehicle stays at garage before scheduled mission',()=>{
  for (const t of [0,2,5,9.99,10]) {
    assert.equal(positionAt(moving,t).x,0);
    assert.equal(positionAt(moving,t).y,0);
  }
});
test('vehicle interpolates only between server dispatch and arrival',()=>{
  assert.equal(positionAt(moving,12).x,50);
  assert.equal(positionAt(moving,12).y,20);
  assert.equal(positionAt(moving,14).phase,'service_start');
  assert.equal(positionAt(moving,17).x,100);
  assert.equal(positionAt(moving,24).y,40);
});
test('time outside actor visibility hides its sprite',()=>{
  assert.equal(positionAt(moving,-1),null);
  assert.equal(positionAt(moving,31),null);
});
