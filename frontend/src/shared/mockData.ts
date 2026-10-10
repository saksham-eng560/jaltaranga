export interface ColonyScenario {
  id: string;
  name: string;
  nameHi: string;
  population: number;
  wetLevelM: number;
  cutoffLevelM: number;
  shelter: string;
  shelterHi: string;
  freeBeds: number;
  route: string;
  routeHi: string;
  avoidRoad: string;
  avoidRoadHi: string;
  coordinates: [number, number];
}

export const REPLAY_STEPS = [
  { label: '12 JUL · 12:00', timestamp: '2023-07-12T12:00:00+05:30', level: 207.54 },
  { label: '12 JUL · 18:00', timestamp: '2023-07-12T18:00:00+05:30', level: 207.81 },
  { label: '13 JUL · 00:00', timestamp: '2023-07-13T00:00:00+05:30', level: 208.2 },
  { label: '13 JUL · 06:00', timestamp: '2023-07-13T06:00:00+05:30', level: 208.4 },
  { label: '13 JUL · 10:00', timestamp: '2023-07-13T10:00:00+05:30', level: 208.53 },
  { label: '13 JUL · 18:00', timestamp: '2023-07-13T18:00:00+05:30', level: 208.66 },
] as const;

export const COLONIES: ColonyScenario[] = [
  {
    id: 'DEL-YP-04',
    name: 'Yamuna Pushta · Sector C',
    nameHi: 'यमुना पुश्ता · सेक्टर सी',
    population: 4200,
    wetLevelM: 208.41,
    cutoffLevelM: 208.71,
    shelter: 'ISBT Relief Camp No. 2',
    shelterHi: 'ISBT राहत शिविर नं. 2',
    freeBeds: 480,
    route: 'Lal Kuan Marg → Kashmere Gate',
    routeHi: 'लाल कुआं मार्ग → कश्मीरी गेट',
    avoidRoad: 'Ring Road',
    avoidRoadHi: 'रिंग रोड',
    coordinates: [77.245, 28.655],
  },
  {
    id: 'DEL-MKT-01',
    name: 'Majnu ka Tilla',
    nameHi: 'मजनू का टीला',
    population: 6800,
    wetLevelM: 208.65,
    cutoffLevelM: 208.95,
    shelter: 'Civil Lines Government School',
    shelterHi: 'सिविल लाइंस सरकारी स्कूल',
    freeBeds: 760,
    route: 'Outer Ring Road → Civil Lines',
    routeHi: 'आउटर रिंग रोड → सिविल लाइंस',
    avoidRoad: 'Yamuna Bazaar Road',
    avoidRoadHi: 'यमुना बाजार रोड',
    coordinates: [77.23, 28.7],
  },
  {
    id: 'DEL-MV-02',
    name: 'Mayur Vihar Extension · Phase 1',
    nameHi: 'मयूर विहार एक्सटेंशन · फेज़ 1',
    population: 11500,
    wetLevelM: 208.95,
    cutoffLevelM: 209.25,
    shelter: 'Akshardham Sports Ground',
    shelterHi: 'अक्षरधाम खेल मैदान',
    freeBeds: 1200,
    route: 'Mayur Vihar Link Road → Akshardham',
    routeHi: 'मयूर विहार लिंक रोड → अक्षरधाम',
    avoidRoad: 'Low-lying river approach',
    avoidRoadHi: 'नदी की निचली पहुंच सड़क',
    coordinates: [77.295, 28.605],
  },
  {
    id: 'DEL-CP-01',
    name: 'Connaught Place',
    nameHi: 'कनॉट प्लेस',
    population: 20000,
    wetLevelM: 216.04,
    cutoffLevelM: 216.34,
    shelter: 'No evacuation required',
    shelterHi: 'निकासी की आवश्यकता नहीं',
    freeBeds: 0,
    route: 'Remain in the safe zone',
    routeHi: 'सुरक्षित क्षेत्र में रहें',
    avoidRoad: 'None reported',
    avoidRoadHi: 'कोई सूचना नहीं',
    coordinates: [77.218, 28.632],
  },
];

export type RiskLevel = 'critical' | 'watch' | 'safe';

export function hoursToWater(level: number, wetLevel: number): number {
  return Math.max(0, (wetLevel - level) / 0.06);
}

export function riskForColony(level: number, wetLevel: number): RiskLevel {
  const hours = hoursToWater(level, wetLevel);
  if (hours <= 4) return 'critical';
  if (hours <= 18) return 'watch';
  return 'safe';
}

export function formatTimeToWater(hours: number, language: 'hi' | 'en'): string {
  if (hours <= 0) return language === 'hi' ? 'पानी पहुंच गया' : 'Water reached';
  if (hours > 24) return language === 'hi' ? '24+ घंटे' : '>24 h';
  return `${hours.toFixed(1)} h`;
}
