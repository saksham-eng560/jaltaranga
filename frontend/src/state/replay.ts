import { create } from 'zustand';
import { DEFAULT_TIMESTAMP, DEFAULT_HERO_COLONY } from '../shared/constants';

interface ReplayState {
  currentTimestamp: string;
  selectedColonyId: string;
  isPlaying: boolean;
  activeView: 'command' | 'colony' | 'compare';
  language: 'hi' | 'en';
  setCurrentTimestamp: (ts: string) => void;
  setSelectedColonyId: (id: string) => void;
  setIsPlaying: (playing: boolean) => void;
  setActiveView: (view: 'command' | 'colony' | 'compare') => void;
  setLanguage: (lang: 'hi' | 'en') => void;
}

export const useReplayStore = create<ReplayState>((set) => ({
  currentTimestamp: DEFAULT_TIMESTAMP,
  selectedColonyId: DEFAULT_HERO_COLONY,
  isPlaying: false,
  activeView: 'command',
  language: 'hi',
  setCurrentTimestamp: (ts) => set({ currentTimestamp: ts }),
  setSelectedColonyId: (id) => set({ selectedColonyId: id }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setActiveView: (view) => set({ activeView: view }),
  setLanguage: (lang) => set({ language: lang }),
}));
