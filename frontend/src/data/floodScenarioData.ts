import type { FeatureCollection } from 'geojson';

export interface ColonyStatusPin {
  id: string;
  name: string;
  status: 'critical' | 'warning' | 'safe'; // red, amber, green
  coordinates: [number, number]; // [lng, lat]
  leadTime?: string;
  population?: string;
}

export interface QueueItem {
  rank: number;
  alertTone: 'red' | 'amber';
  colonyName: string;
  leadTime: string;
  population: string;
  colonyId: string;
}

export interface ReplayTimelineStep {
  id: string;
  buttonLabel: string;
  dateLabel: string;
  timeLabel: string;
  dateTimeDisplay: string;
  waterLevel: string;
  waterLevelDelta: string;
  danger: string;
  dangerTone: 'red' | 'amber' | 'green';
  affectedPopulation: string;
  boatsDeployed: string;
  scrubberWaterLevel: string;
  scrubberTime: string;
  warningBox: {
    title: string;
    message: string;
  };
  queue: QueueItem[];
  dispatch: {
    status: string;
    statusHi: string;
    messageEn: string;
    messageHi: string;
    camp: string;
    alternateRoute: string;
  };
  floodGeoJson: FeatureCollection;
  pins: ColonyStatusPin[];
}

// Meandering flood geometry for the Yamuna River in Delhi
const FLOOD_STEP_JUN15: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Yamuna River Swollen Channel - Jun 15', depth_class: '0.3-1' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.230, 28.715],
            [77.228, 28.700],
            [77.232, 28.682],
            [77.236, 28.668],
            [77.240, 28.654],
            [77.245, 28.638],
            [77.250, 28.620],
            [77.260, 28.600],
            [77.275, 28.575],
            [77.300, 28.550],
            [77.308, 28.552],
            [77.288, 28.578],
            [77.272, 28.605],
            [77.262, 28.628],
            [77.256, 28.650],
            [77.250, 28.670],
            [77.246, 28.688],
            [77.242, 28.705],
            [77.238, 28.718],
            [77.230, 28.715],
          ],
        ],
      },
    },
  ],
};

const FLOOD_STEP_JUN16: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Yamuna Inundation - Jun 16 (207.25m)', depth_class: '1-2' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.226, 28.718],
            [77.223, 28.702],
            [77.226, 28.685],
            [77.232, 28.670],
            [77.238, 28.656],
            [77.243, 28.642],
            [77.248, 28.624],
            [77.258, 28.602],
            [77.275, 28.578],
            [77.305, 28.548],
            [77.318, 28.548],
            [77.295, 28.580],
            [77.280, 28.610],
            [77.268, 28.635],
            [77.262, 28.656],
            [77.256, 28.678],
            [77.252, 28.698],
            [77.244, 28.712],
            [77.236, 28.720],
            [77.226, 28.718],
          ],
        ],
      },
    },
  ],
};

// Historic Peak Flood: June 17, 2024 / July 2023 peak level 208.52m!
// Submerges Yamuna Bazar, ISBT / Monastery Market, Lal Qila floodplain, Ring Road severed, Geeta Colony & Mayur Vihar!
const FLOOD_STEP_JUN17_PEAK: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    // Outer Flood Water Boundary (radiant blue matching target UI)
    {
      type: 'Feature',
      properties: { name: 'Historic Delhi Flood Peak - 208.52m Extent', depth_class: '>2' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            // Northern Reach: Wazirabad
            [77.224, 28.720],
            [77.221, 28.708],
            [77.223, 28.694],
            // West bank: Monastery Market & ISBT breach
            [77.226, 28.680],
            [77.228, 28.671],
            [77.232, 28.665],
            // Yamuna Bazar breach across Ring Road
            [77.236, 28.660],
            [77.238, 28.654],
            // Lal Qila / Red Fort outer flood plain
            [77.240, 28.648],
            [77.242, 28.642],
            // Rajghat & Vikas Minar embankment
            [77.246, 28.632],
            [77.250, 28.620],
            // ITO Barrage flood basin
            [77.256, 28.605],
            // Nizamuddin & Barapullah confluence
            [77.268, 28.588],
            [77.284, 28.570],
            [77.306, 28.552],
            [77.324, 28.542],
            // East bank return path: Okhla barrage
            [77.330, 28.548],
            [77.318, 28.566],
            // Mayur Vihar-I & II broad Khadar flood plains
            [77.306, 28.590],
            [77.300, 28.608],
            [77.294, 28.622],
            [77.286, 28.638],
            // Geeta Colony & Shakarpur East bank
            [77.276, 28.650],
            [77.270, 28.664],
            [77.264, 28.678],
            // Usmanpur Floodplain Basti
            [77.258, 28.692],
            [77.252, 28.705],
            [77.244, 28.718],
            [77.232, 28.722],
            [77.224, 28.720],
          ],
          // Interior unflooded sandbar / elevated river island ridge (matching UI hole)
          [
            [77.246, 28.668],
            [77.248, 28.658],
            [77.252, 28.645],
            [77.256, 28.632],
            [77.254, 28.642],
            [77.250, 28.656],
            [77.248, 28.665],
            [77.246, 28.668],
          ],
        ],
      },
    },
    // Deep Main River Torrent Core
    {
      type: 'Feature',
      properties: { name: 'Deep Channel Surge', depth_class: '1-2' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.228, 28.715],
            [77.225, 28.700],
            [77.230, 28.675],
            [77.236, 28.660],
            [77.242, 28.642],
            [77.248, 28.622],
            [77.258, 28.600],
            [77.278, 28.574],
            [77.302, 28.552],
            [77.314, 28.548],
            [77.296, 28.574],
            [77.276, 28.602],
            [77.264, 28.626],
            [77.256, 28.648],
            [77.248, 28.670],
            [77.242, 28.692],
            [77.236, 28.712],
            [77.228, 28.715],
          ],
        ],
      },
    },
    // West Bank Local Flood Bulge: Kashmiri Gate, Yamuna Bazar & Lal Qila
    {
      type: 'Feature',
      properties: { name: 'Ring Road / Yamuna Bazar Submersion Area', depth_class: '>2' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.231, 28.668],
            [77.238, 28.665],
            [77.243, 28.656],
            [77.242, 28.648],
            [77.237, 28.652],
            [77.232, 28.660],
            [77.231, 28.668],
          ],
        ],
      },
    },
    // East Bank Local Flood Bulge: Geeta Colony & Mayur Vihar-I
    {
      type: 'Feature',
      properties: { name: 'Mayur Vihar & Geeta Colony Submersion Area', depth_class: '>2' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.262, 28.650],
            [77.274, 28.642],
            [77.288, 28.630],
            [77.298, 28.615],
            [77.302, 28.605],
            [77.292, 28.612],
            [77.280, 28.625],
            [77.268, 28.638],
            [77.262, 28.650],
          ],
        ],
      },
    },
  ],
};

const FLOOD_STEP_JUN18: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Receding Flood Inundation - Jun 18 (207.80m)', depth_class: '1-2' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.225, 28.718],
            [77.222, 28.704],
            [77.225, 28.686],
            [77.230, 28.672],
            [77.235, 28.658],
            [77.241, 28.646],
            [77.246, 28.630],
            [77.254, 28.612],
            [77.268, 28.592],
            [77.290, 28.568],
            [77.315, 28.546],
            [77.322, 28.550],
            [77.298, 28.576],
            [77.280, 28.605],
            [77.270, 28.632],
            [77.264, 28.652],
            [77.256, 28.676],
            [77.250, 28.694],
            [77.242, 28.710],
            [77.234, 28.718],
            [77.225, 28.718],
          ],
        ],
      },
    },
  ],
};

export const TIMELINE_STEPS: ReplayTimelineStep[] = [
  {
    id: 'step-jun-15',
    buttonLabel: 'JUN 15 (08:00)',
    dateLabel: 'JUN 15',
    timeLabel: '(08:00)',
    dateTimeDisplay: 'June 15, 2024 | 08:00',
    waterLevel: '205.10m',
    waterLevelDelta: '(▲ +0.12m)',
    danger: 'WARNING',
    dangerTone: 'amber',
    affectedPopulation: '34,200',
    boatsDeployed: '24',
    scrubberWaterLevel: '205.10m',
    scrubberTime: '08:00',
    warningBox: {
      title: 'Amber Warning Box',
      message: '⚠ YAMUNA WATER RISING - Khadar settlements advised to monitor sirens',
    },
    queue: [
      {
        rank: 1,
        alertTone: 'amber',
        colonyName: 'Majnu Ka Tila',
        leadTime: '6.5h',
        population: '6,500',
        colonyId: 'DEL-MKT-01',
      },
      {
        rank: 2,
        alertTone: 'amber',
        colonyName: 'Usmanpur',
        leadTime: '7.2h',
        population: '8,900',
        colonyId: 'DEL-USM-05',
      },
      {
        rank: 3,
        alertTone: 'amber',
        colonyName: 'Yamuna Bazar',
        leadTime: '8.0h',
        population: '12,450',
        colonyId: 'DEL-YP-04',
      },
      {
        rank: 4,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-I',
        leadTime: '9.4h',
        population: '15,200',
        colonyId: 'DEL-MV-01',
      },
      {
        rank: 5,
        alertTone: 'amber',
        colonyName: 'Geeta Colony',
        leadTime: '10.1h',
        population: '8,100',
        colonyId: 'DEL-GC-06',
      },
    ],
    dispatch: {
      status: 'ADVISORY (परामर्श)',
      statusHi: 'परामर्श',
      messageEn: 'Alert for Majnu Ka Tila & Usmanpur. Prepare emergency bags and keep cattle away from the river bank.',
      messageHi: 'मजनू का टीला और उस्मानपुर के लिए अलर्ट। आपातकालीन बैग तैयार रखें और मवेशियों को नदी तट से दूर रखें।',
      camp: 'RC-1 Majnu Ka Tila Community Hall',
      alternateRoute: 'Outer Ring Road (North)',
    },
    floodGeoJson: FLOOD_STEP_JUN15,
    pins: [
      { id: 'DEL-MKT-01', name: 'Majnu Ka Tila', status: 'warning', coordinates: [77.228, 28.700], leadTime: '6.5h', population: '6,500' },
      { id: 'DEL-USM-05', name: 'Usmanpur', status: 'warning', coordinates: [77.252, 28.685], leadTime: '7.2h', population: '8,900' },
      { id: 'DEL-YP-04', name: 'Yamuna Bazar', status: 'warning', coordinates: [77.241, 28.6565], leadTime: '8.0h', population: '12,450' },
      { id: 'DEL-MV-01', name: 'Mayur Vihar-I', status: 'safe', coordinates: [77.295, 28.605], leadTime: '9.4h', population: '15,200' },
      { id: 'DEL-GC-06', name: 'Geeta Colony', status: 'safe', coordinates: [77.260, 28.648], leadTime: '10.1h', population: '8,100' },
      { id: 'CAMP-RC-4', name: 'RC-4 Relief Camp', status: 'safe', coordinates: [77.2405, 28.644] },
      { id: 'CAMP-CL-01', name: 'Civil Lines Govt Camp', status: 'safe', coordinates: [77.222, 28.675] },
    ],
  },
  {
    id: 'step-jun-16',
    buttonLabel: 'JUN 16 (12:00)',
    dateLabel: 'JUN 16',
    timeLabel: '(12:00)',
    dateTimeDisplay: 'June 16, 2024 | 12:00',
    waterLevel: '207.25m',
    waterLevelDelta: '(▲ +0.25m)',
    danger: 'HIGH',
    dangerTone: 'amber',
    affectedPopulation: '78,500',
    boatsDeployed: '68',
    scrubberWaterLevel: '207.25m',
    scrubberTime: '12:00',
    warningBox: {
      title: 'Amber Warning Box',
      message: '⚠ RING ROAD VULNERABLE - Speed Restricted near ISBT Khadar',
    },
    queue: [
      {
        rank: 1,
        alertTone: 'red',
        colonyName: 'Yamuna Bazar',
        leadTime: '4.8h',
        population: '12,450',
        colonyId: 'DEL-YP-04',
      },
      {
        rank: 2,
        alertTone: 'red',
        colonyName: 'Usmanpur',
        leadTime: '5.2h',
        population: '8,900',
        colonyId: 'DEL-USM-05',
      },
      {
        rank: 3,
        alertTone: 'amber',
        colonyName: 'Monastery Market',
        leadTime: '5.5h',
        population: '4,800',
        colonyId: 'DEL-MON-03',
      },
      {
        rank: 4,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-I',
        leadTime: '6.8h',
        population: '15,200',
        colonyId: 'DEL-MV-01',
      },
      {
        rank: 5,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-II',
        leadTime: '7.0h',
        population: '15,200',
        colonyId: 'DEL-MV-02',
      },
    ],
    dispatch: {
      status: 'PENDING APPROVAL (प्रतीक्षारत)',
      statusHi: 'प्रतीक्षारत',
      messageEn: 'Evacuate low-lying Yamuna Bazar sectors to designated shelter camps. Avoid Bela Road.',
      messageHi: 'निचले यमुना बाज़ार क्षेत्रों को खाली करें और निर्दिष्ट राहत शिविरों में जाएं। बेला रोड से बचें।',
      camp: 'RC-2 Kashmiri Gate School',
      alternateRoute: 'Shyama Prasad Mukherjee Marg',
    },
    floodGeoJson: FLOOD_STEP_JUN16,
    pins: [
      { id: 'DEL-YP-04', name: 'Yamuna Bazar', status: 'critical', coordinates: [77.241, 28.6565], leadTime: '4.8h', population: '12,450' },
      { id: 'DEL-USM-05', name: 'Usmanpur', status: 'critical', coordinates: [77.252, 28.685], leadTime: '5.2h', population: '8,900' },
      { id: 'DEL-MON-03', name: 'Monastery Market', status: 'warning', coordinates: [77.2305, 28.6705], leadTime: '5.5h', population: '4,800' },
      { id: 'DEL-MV-01', name: 'Mayur Vihar-I', status: 'warning', coordinates: [77.295, 28.605], leadTime: '6.8h', population: '15,200' },
      { id: 'DEL-MV-02', name: 'Mayur Vihar-II', status: 'warning', coordinates: [77.302, 28.618], leadTime: '7.0h', population: '15,200' },
      { id: 'CAMP-RC-4', name: 'RC-4 Relief Camp', status: 'safe', coordinates: [77.2405, 28.644] },
      { id: 'CAMP-CL-01', name: 'Civil Lines Camp', status: 'safe', coordinates: [77.222, 28.675] },
    ],
  },
  {
    // The exact canonical state shown in user's UI screenshot!
    id: 'step-jun-17',
    buttonLabel: 'JUN 17 (16:00)',
    dateLabel: 'JUN 17',
    timeLabel: '(16:00)',
    dateTimeDisplay: 'June 17, 2024 | 16:35',
    waterLevel: '208.52m',
    waterLevelDelta: '(▲ +0.32m)',
    danger: 'EXTREME',
    dangerTone: 'red',
    affectedPopulation: '112,450',
    boatsDeployed: '104',
    scrubberWaterLevel: '208.20m',
    scrubberTime: '16:30',
    warningBox: {
      title: 'Amber Warning Box',
      message: '⚠ RING ROAD SEVERED - Use Alternate Route (Noida Link Rd)',
    },
    queue: [
      {
        rank: 1,
        alertTone: 'red',
        colonyName: 'Yamuna Bazar',
        leadTime: '3.5h',
        population: '12,450',
        colonyId: 'DEL-YP-04',
      },
      {
        rank: 2,
        alertTone: 'red',
        colonyName: 'Usmanpur',
        leadTime: '4.2h',
        population: '8,900',
        colonyId: 'DEL-USM-05',
      },
      {
        rank: 3,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-I',
        leadTime: '5.1h',
        population: '15,200',
        colonyId: 'DEL-MV-01',
      },
      {
        rank: 4,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-II',
        leadTime: '5.1h',
        population: '15,200',
        colonyId: 'DEL-MV-02',
      },
      {
        rank: 5,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-II',
        leadTime: '5.1h',
        population: '15,200',
        colonyId: 'DEL-MV-03',
      },
    ],
    dispatch: {
      status: 'APPROVED (अनुमोदित)',
      statusHi: 'अनुमोदित',
      messageEn: 'Evacuate Yamuna Bazar (Zone 1) immediately to relief camp RC-4. Utilize Alternate Route.',
      messageHi: 'यमुना बाज़ार (ज़ोन 1) को तुरंत खाली करें और राहत शिविर RC-4 पर जाएं। वैकल्पिक मार्ग का उपयोग करें।',
      camp: 'Relief Camp RC-4 (Daryaganj Shelter)',
      alternateRoute: 'Noida Link Rd / Vikas Marg',
    },
    floodGeoJson: FLOOD_STEP_JUN17_PEAK,
    pins: [
      // Red pins: Critical
      { id: 'DEL-YP-04', name: 'Yamuna Bazar', status: 'critical', coordinates: [77.2395, 28.6580], leadTime: '3.5h', population: '12,450' },
      { id: 'DEL-USM-05', name: 'Usmanpur', status: 'critical', coordinates: [77.2510, 28.6870], leadTime: '4.2h', population: '8,900' },
      { id: 'DEL-ISBT-01', name: 'ISBT Kashmiri Gate', status: 'critical', coordinates: [77.2340, 28.6720], leadTime: '2.8h', population: '18,500' },
      { id: 'DEL-LQ-01', name: 'Lal Qila Floodplain', status: 'critical', coordinates: [77.2415, 28.6510], leadTime: '3.1h', population: '14,200' },
      { id: 'DEL-BELA-01', name: 'Bela Road Cutoff', status: 'critical', coordinates: [77.2450, 28.6390], leadTime: '2.5h', population: '7,800' },
      // Amber pins: Warning
      { id: 'DEL-MV-01', name: 'Mayur Vihar-I', status: 'warning', coordinates: [77.2940, 28.6080], leadTime: '5.1h', population: '15,200' },
      { id: 'DEL-MV-02', name: 'Mayur Vihar-II', status: 'warning', coordinates: [77.3020, 28.6180], leadTime: '5.1h', population: '15,200' },
      { id: 'DEL-GC-06', name: 'Geeta Colony', status: 'warning', coordinates: [77.2640, 28.6530], leadTime: '5.4h', population: '8,100' },
      { id: 'DEL-SHASTRI', name: 'Shastri Park Khadar', status: 'warning', coordinates: [77.2560, 28.6710], leadTime: '4.9h', population: '11,200' },
      { id: 'DEL-KK-01', name: 'Khajuri Khas', status: 'warning', coordinates: [77.2620, 28.7050], leadTime: '6.0h', population: '11,000' },
      // Green pins: Safe / Relief Camps
      { id: 'CAMP-RC-4', name: 'RC-4 Daryaganj Camp', status: 'safe', coordinates: [77.2405, 28.6410], population: 'Cap: 2,500' },
      { id: 'CAMP-CL-01', name: 'Civil Lines Govt Camp', status: 'safe', coordinates: [77.2240, 28.6780], population: 'Cap: 3,000' },
      { id: 'CAMP-AK-01', name: 'Akshardham Relief Ground', status: 'safe', coordinates: [77.2800, 28.6140], population: 'Cap: 5,000' },
      { id: 'SAFE-CP-01', name: 'Connaught Place Safe Zone', status: 'safe', coordinates: [77.2180, 28.6320], population: 'High Ground' },
    ],
  },
  {
    id: 'step-jun-18',
    buttonLabel: 'JUN 18 (20:00)',
    dateLabel: 'JUN 18',
    timeLabel: '(20:00)',
    dateTimeDisplay: 'June 18, 2024 | 20:00',
    waterLevel: '207.80m',
    waterLevelDelta: '(▼ -0.15m)',
    danger: 'HIGH',
    dangerTone: 'amber',
    affectedPopulation: '94,100',
    boatsDeployed: '85',
    scrubberWaterLevel: '207.80m',
    scrubberTime: '20:00',
    warningBox: {
      title: 'Amber Warning Box',
      message: '⚠ RECEDING WATER - Ring Road dewatering in progress. Remain in shelters.',
    },
    queue: [
      {
        rank: 1,
        alertTone: 'red',
        colonyName: 'Yamuna Bazar',
        leadTime: '4.0h',
        population: '12,450',
        colonyId: 'DEL-YP-04',
      },
      {
        rank: 2,
        alertTone: 'amber',
        colonyName: 'Usmanpur',
        leadTime: '5.5h',
        population: '8,900',
        colonyId: 'DEL-USM-05',
      },
      {
        rank: 3,
        alertTone: 'amber',
        colonyName: 'Geeta Colony',
        leadTime: '6.0h',
        population: '8,100',
        colonyId: 'DEL-GC-06',
      },
      {
        rank: 4,
        alertTone: 'amber',
        colonyName: 'Mayur Vihar-I',
        leadTime: '6.5h',
        population: '15,200',
        colonyId: 'DEL-MV-01',
      },
      {
        rank: 5,
        alertTone: 'amber',
        colonyName: 'Bela Estate',
        leadTime: '7.2h',
        population: '5,400',
        colonyId: 'DEL-BE-07',
      },
    ],
    dispatch: {
      status: 'APPROVED (अनुमोदित)',
      statusHi: 'अनुमोदित',
      messageEn: 'Flood waters receding slowly. Keep relief camps operational. Do not re-enter flooded houses until certified safe.',
      messageHi: 'बाढ़ का पानी धीरे-धीरे कम हो रहा है। राहत शिविर चालू रखें। सुरक्षित प्रमाणित होने तक बाढ़ प्रभावित घरों में न जाएं।',
      camp: 'Relief Camp RC-4 & Civil Lines',
      alternateRoute: 'Vikas Marg (Restricted)',
    },
    floodGeoJson: FLOOD_STEP_JUN18,
    pins: [
      { id: 'DEL-YP-04', name: 'Yamuna Bazar', status: 'critical', coordinates: [77.2395, 28.6580], leadTime: '4.0h', population: '12,450' },
      { id: 'DEL-USM-05', name: 'Usmanpur', status: 'warning', coordinates: [77.2510, 28.6870], leadTime: '5.5h', population: '8,900' },
      { id: 'DEL-GC-06', name: 'Geeta Colony', status: 'warning', coordinates: [77.2640, 28.6530], leadTime: '6.0h', population: '8,100' },
      { id: 'DEL-MV-01', name: 'Mayur Vihar-I', status: 'warning', coordinates: [77.2940, 28.6080], leadTime: '6.5h', population: '15,200' },
      { id: 'DEL-BE-07', name: 'Bela Estate', status: 'warning', coordinates: [77.2450, 28.6390], leadTime: '7.2h', population: '5,400' },
      { id: 'CAMP-RC-4', name: 'RC-4 Relief Camp', status: 'safe', coordinates: [77.2405, 28.6410] },
      { id: 'CAMP-CL-01', name: 'Civil Lines Camp', status: 'safe', coordinates: [77.2240, 28.6780] },
    ],
  },
];
