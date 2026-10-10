import React from 'react';
import { useReplayStore } from '../state/replay';
import { t } from '../i18n/t';

const TIMESTAMPS = [
  { label: '12 Jul 12:00', ts: '2023-07-12T12:00:00+05:30', level: '207.54 m' },
  { label: '12 Jul 18:00', ts: '2023-07-12T18:00:00+05:30', level: '207.81 m' },
  { label: '13 Jul 00:00 (Golden)', ts: '2023-07-13T00:00:00+05:30', level: '208.20 m' },
  { label: '13 Jul 06:00', ts: '2023-07-13T06:00:00+05:30', level: '208.40 m' },
  { label: '13 Jul 10:00', ts: '2023-07-13T10:00:00+05:30', level: '208.53 m' },
  { label: '13 Jul 18:00 (Peak HFL)', ts: '2023-07-13T18:00:00+05:30', level: '208.66 m' },
];

export const TimelineScrubber: React.FC = () => {
  const { currentTimestamp, setCurrentTimestamp, language } = useReplayStore();

  const currentIndex = TIMESTAMPS.findIndex((item) => item.ts === currentTimestamp);
  const activeItem = TIMESTAMPS[currentIndex >= 0 ? currentIndex : 2];

  return (
    <div
      style={{
        padding: '12px 24px',
        background: '#1e293b',
        borderTop: '1px solid #334155',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
            {t('replay_badge', language)}
          </span>
          <h3 style={{ fontSize: '1.1rem', color: '#38bdf8' }}>
            {activeItem.label} · Stage: {activeItem.level}
          </h3>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {TIMESTAMPS.map((item, idx) => (
            <button
              key={item.ts}
              onClick={() => setCurrentTimestamp(item.ts)}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                backgroundColor: item.ts === currentTimestamp ? '#0284c7' : '#334155',
                color: '#ffffff',
                transition: 'background 0.2s',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
