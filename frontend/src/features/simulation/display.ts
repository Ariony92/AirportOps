/** Pure visual interpolation between server-scheduled animation keyframes. */
import type { Track, Keyframe } from './types';
export function positionAt(track: Track, minute: number): Keyframe | null {
  if (minute < track.visible_from || minute > track.visible_until || !track.keyframes.length) return null;
  const frames = track.keyframes;
  const first = frames[0];
  if (minute <= first.minute) return first;
  const last = frames[frames.length - 1];
  if (minute >= last.minute) return last;
  for (let i = 1; i < frames.length; i++) {
    const next = frames[i];
    if (minute <= next.minute) {
      const prev = frames[i - 1];
      const fraction = next.minute === prev.minute ? 1 : (minute - prev.minute) / (next.minute - prev.minute);
      return { ...prev, x: prev.x + (next.x - prev.x) * fraction,
        y: prev.y + (next.y - prev.y) * fraction,
        phase: fraction >= 1 ? next.phase : prev.phase };
    }
  }
  return last;
}
