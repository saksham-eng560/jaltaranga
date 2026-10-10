import { create } from 'zustand';
import type { Manifest } from '../shared/types';
import { readReplayTime, snapToValidAt, writeReplayTime } from '../lib/replay';

interface ReplayState {
  manifest: Manifest | null;
  at: string;
  playing: boolean;
  speed: number;
  setManifest: (manifest: Manifest) => void;
  setAt: (at: string, push?: boolean) => void;
  step: (direction: -1 | 1) => void;
  setPlaying: (playing: boolean) => void;
}

export const useReplay = create<ReplayState>((set, get) => ({
  manifest: null,
  at: '',
  playing: false,
  speed: 1,
  setManifest: (manifest) => {
    const at = readReplayTime(manifest);
    writeReplayTime(at);
    set({ manifest, at });
  },
  setAt: (requested, push = true) => {
    const { manifest } = get();
    if (!manifest) return;
    const at = snapToValidAt(requested, manifest.valid_at);
    writeReplayTime(at, !push);
    set({ at });
  },
  step: (direction) => {
    const { manifest, at, setAt } = get();
    if (!manifest) return;
    const index = manifest.valid_at.indexOf(at);
    const target = Math.max(0, Math.min(manifest.valid_at.length - 1, index + direction));
    setAt(manifest.valid_at[target]);
  },
  setPlaying: (playing) => set({ playing }),
}));
