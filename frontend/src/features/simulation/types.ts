export type Keyframe = { minute: number; x: number; y: number; phase: string; label: string };
export type Track = { id: string; kind: 'aircraft' | 'vehicle'; label: string; keyframes: Keyframe[]; visible_from: number; visible_until: number };
export type Event = { flight_number: string; minute: number; phase: string; details: string; vehicle: string | null };
export type Flight = { flight_number: string; gate: number | null; runway: string | null; status: string; reason: string | null; landing_minute: number | null; takeoff_minute: number | null; delay_min: number };
export type Playback = { version: number; duration_minutes: number; tracks: Track[]; timeline: Event[]; flights: Flight[]; kpis: Record<string, number>; strategy: 'baseline' | 'optimized'; note: string };
