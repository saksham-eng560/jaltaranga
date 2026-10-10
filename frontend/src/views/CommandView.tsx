import React, { useState } from 'react';
import { MapView } from '../map/MapView';
import { TimelineScrubber } from '../components/TimelineScrubber';
import { DispatchCardView } from '../components/DispatchCard';
import { useReplayStore } from '../state/replay';
import { t } from '../i18n/t';

interface ColonyItem {
  id: string;
  name: string;
  name_hi: string;
  pop: number;
  t_sub: string;
  status: 'red' | 'amber' | 'green';
  shelter: string;
}

const SAMPLE_PLANS: ColonyItem[] = [
  {
    id: 'DEL-YP-04',
    name: 'Yamuna Pushta Sector C',
    name_hi: 'यमुना पुश्ता सेक्टर सी',
    pop: 4200,
    t_sub: '3.5 h',
    status: 'red',
    shelter: 'ISBT Relief Camp #2',
  },
  {
    id: 'DEL-MKT-01',
    name: 'Majnu ka Tilla',
    name_hi: 'मजनू का टीला',
    pop: 6800,
    t_sub: '5.2 h',
    status: 'amber',
    shelter: 'Civil Lines Govt School',
  },
  {
    id: 'DEL-MV-02',
    name: 'Mayur Vihar Ext Phase 1',
    name_hi: 'मयूर विहार एक्सटेंशन फेज 1',
    pop: 11500,
    t_sub: '8.0 h',
    status: 'amber',
    shelter: 'Akshardham Sports Ground',
  },
  {
    id: 'DEL-CP-01',
    name: 'Connaught Place',
    name_hi: 'कनॉट प्लेस',
    pop: 20000,
    t_sub: 'Dry (>24h)',
    status: 'green',
    shelter: 'N/A (Safe Zone)',
  },
];

export const CommandView: React.FC = () => {
  const { selectedColonyId, setSelectedColonyId, language } = useReplayStore();
  const selectedColony = SAMPLE_PLANS.find((c) => c.id === selectedColonyId) || SAMPLE_PLANS[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      {/* Top Main Workspace */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Sidebar: Ranked Colony Evacuation Plans */}
        <div
          style={{
            width: '340px',
            background: '#1e293b',
            borderRight: '1px solid #334155',
            padding: '16px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', color: '#f8fafc' }}>🚨 Priority Evacuation Queue</h3>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Ranked by T_sub</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {SAMPLE_PLANS.map((colony) => {
              const isSelected = colony.id === selectedColony.id;
              return (
                <div
                  key={colony.id}
                  onClick={() => setSelectedColonyId(colony.id)}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    background: isSelected ? '#0f172a' : '#334155',
                    border: isSelected ? '1px solid #38bdf8' : '1px solid transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                      {language === 'hi' ? colony.name_hi : colony.name}
                    </span>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color:
                          colony.status === 'red'
                            ? '#ef4444'
                            : colony.status === 'amber'
                              ? '#f59e0b'
                              : '#10b981',
                      }}
                    >
                      {colony.t_sub}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#94a3b8' }}>
                    <span>Pop: {colony.pop.toLocaleString()}</span>
                    <span>Shelter: {colony.shelter}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div
            style={{
              marginTop: 'auto',
              padding: '12px',
              borderRadius: '8px',
              background: '#451a03',
              border: '1px solid #b45309',
            }}
          >
            <div style={{ fontWeight: 600, color: '#fde047', fontSize: '0.85rem' }}>
              ⚠️ Ring Road Severed (Cutoff 0.3m)
            </div>
            <div style={{ fontSize: '0.75rem', color: '#fef08a', marginTop: '2px' }}>
              ISBT approach road submerged. Routing diverted to Lal Kuan Marg.
            </div>
          </div>
        </div>

        {/* Center: Interactive 2.5D Map Engine */}
        <div style={{ flex: 1, position: 'relative' }}>
          <MapView
            selectedColonyId={selectedColony.id}
            onSelectColony={(id) => setSelectedColonyId(id)}
          />
        </div>

        {/* Right Sidebar: Plan Inspection & Validated Dispatch */}
        <div
          style={{
            width: '380px',
            background: '#1e293b',
            borderLeft: '1px solid #334155',
            padding: '16px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Selected Sector</span>
            <h2 style={{ fontSize: '1.25rem', color: '#38bdf8' }}>
              {language === 'hi' ? selectedColony.name_hi : selectedColony.name}
            </h2>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '8px',
            }}
          >
            <div style={{ background: '#0f172a', padding: '10px', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{t('time_to_water', language)}</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ef4444' }}>
                {selectedColony.t_sub}
              </div>
            </div>
            <div style={{ background: '#0f172a', padding: '10px', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{t('free_beds', language)}</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981' }}>
                480 / 1200
              </div>
            </div>
          </div>

          {/* Validated Slot-Filled Dispatch Card */}
          <DispatchCardView colonyName={language === 'hi' ? selectedColony.name_hi : selectedColony.name} />
        </div>
      </div>

      {/* Bottom Timeline Replay Scrubber */}
      <TimelineScrubber />
    </div>
  );
};
