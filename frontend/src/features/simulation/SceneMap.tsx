import { useMemo } from 'react';
import type { Keyframe, Track } from './types';
import { positionAt } from './display';

/** Coordinate interpolation is only an SVG rendering concern; all timed actions come from the API. */
export default function SceneMap({ tracks, minute, selected, onSelect }: {
  tracks: Track[]; minute: number; selected: string | null; onSelect: (value: string) => void;
}) {
  const actors = useMemo(() => tracks.map(track => ({ track, point: positionAt(track, minute) }))
    .filter((item): item is { track: Track; point: Keyframe } => item.point !== null), [tracks, minute]);
  return <div className="live-map">
    <div className="map-heading"><span>● TRAJECTOIRES PLANIFIÉES</span><span>06:00 + TEMPS SIMULÉ</span></div>
    <svg viewBox="0 0 900 470" role="img" aria-label="Plan animé des cinq portes, appareils et véhicules affectés aux opérations">
      <defs><pattern id="tarmac-grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#294451" strokeWidth=".65" /></pattern>
        <filter id="plane-shadow"><feDropShadow dx="0" dy="5" stdDeviation="4" floodOpacity=".4" /></filter>
      </defs>
      <rect width="900" height="470" fill="#0b2432"/><rect width="900" height="470" fill="url(#tarmac-grid)"/>
      <rect x="28" y="36" width="844" height="60" rx="12" fill="#1c3a47" stroke="#40616b"/>
      <text x="450" y="62" textAnchor="middle" className="svg-terminal">TERMINAL 01</text><text x="450" y="81" textAnchor="middle" className="svg-sub">AIRPORTOPS • PLATEFORME PÉDAGOGIQUE</text>
      <rect x="24" y="355" width="852" height="76" rx="7" fill="#293b45"/><path d="M40 390H859" stroke="#ffe6a0" strokeWidth="3" strokeDasharray="24 18"/>
      <text x="48" y="373" className="svg-runway">PISTE • MOUVEMENTS</text>
      <path d="M50 285H850" stroke="#dbc078" strokeWidth="8" strokeLinecap="round" opacity=".24"/><path d="M50 285H850" stroke="#dbc078" strokeWidth="2" strokeDasharray="11 9"/>
      <path d="M450 285V355" stroke="#dbc078" strokeWidth="5" strokeDasharray="8 8" opacity=".65"/>
      {Array.from({length:5},(_,i) => { const x = 112+i*170; const active = actors.find(({track,point}) => track.kind === 'aircraft' && Math.abs(point.x-x) < 7 && Math.abs(point.y-187)<7);
        return <g key={i}><path d={`M${x} 99V284`} stroke="#3d6672" strokeWidth="9"/><path d={`M${x} 99V284`} stroke="#cfaf70" strokeWidth="1.5" strokeDasharray="7 11"/>
          <rect x={x-57} y="110" width="114" height="115" rx="12" fill={active?'#1b555c':'#143440'} stroke={active?'#4de0bf':'#436671'} strokeWidth="2"/>
          <text x={x} y="133" className="svg-gate">PORTE {String(i+1).padStart(2,'0')}</text>
          {!active && <text x={x} y="192" className="svg-free">LIBRE</text>}
        </g>; })}
      <g><rect x="388" y="259" width="124" height="45" rx="8" fill="#223c47" stroke="#4e6b76"/><text x="450" y="278" className="svg-depot">AIRE SERVICES</text><text x="450" y="294" className="svg-depot">VÉHICULES</text></g>
      {actors.map(({track,point}) => <g key={track.id} role="button" tabIndex={0} onClick={()=>onSelect(track.id)} onKeyDown={e=>{ if(e.key==='Enter')onSelect(track.id); }} aria-label={`${track.kind==='aircraft'?'Vol':'Véhicule'} ${track.label}: ${point.phase}`} transform={`translate(${point.x} ${point.y})`} className={`scene-actor ${selected === track.id ? 'chosen' : ''}`}>
        {track.kind === 'aircraft' ? <g filter="url(#plane-shadow)"><path d="M0-32 L6-27 L9-7 L34 7 L34 14 L9 11 L7 30 L14 37 L14 42 L0 38 L-14 42 L-14 37 L-7 30 L-9 11 L-34 14 L-34 7 L-9-7 L-6-27Z" fill="#67f2cf" stroke="#e7fff7" strokeWidth="2"/><circle cx="0" cy="-21" r="3" fill="#eafffb"/></g>
          : <g><rect x="-14" y="-10" width="28" height="19" rx="5" fill="#f9ba63" stroke="#ffe5ae" strokeWidth="1.5"/><rect x="-8" y="-15" width="14" height="7" rx="2" fill="#dfe9ec"/><circle cx="-9" cy="11" r="4" fill="#06151c"/><circle cx="9" cy="11" r="4" fill="#06151c"/></g>}
        <text x="0" y="-43" className="svg-actor-label">{track.label}</text>
      </g>)}
      <text x="35" y="456" className="svg-legend">VISUALISATION SCHÉMATIQUE • TEMPS DÉRIVÉS DU BACKEND</text>
    </svg>
    <div className="map-bottom"><span><i className="dot green"/>Avion planifié</span><span><i className="dot amber"/>Véhicule affecté</span><span><i className="dot slate"/>Position stable hors mission</span></div>
  </div>;
}
