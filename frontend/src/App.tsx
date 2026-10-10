import React from 'react';
import { useReplayStore } from './state/replay';
import { CommandView } from './views/CommandView';
import { ColonyView } from './views/ColonyView';
import { t } from './i18n/t';

export const App: React.FC = () => {
  const { activeView, setActiveView, language, setLanguage } = useReplayStore();

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <nav
        style={{
          background: '#0f172a',
          borderBottom: '1px solid #334155',
          padding: '10px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          height: '56px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1 style={{ fontSize: '1.2rem', color: '#38bdf8', fontWeight: 800 }}>
            🌊 जलतरंग (Jaltaranga)
          </h1>
          <span
            style={{
              fontSize: '0.75rem',
              background: '#b91c1c',
              color: '#ffffff',
              padding: '2px 8px',
              borderRadius: '4px',
              fontWeight: 700,
            }}
          >
            DEMO REPLAY
          </span>
        </div>

        {/* View Switcher Chips */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveView('command')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
              background: activeView === 'command' ? '#0284c7' : '#1e293b',
              color: activeView === 'command' ? '#ffffff' : '#94a3b8',
            }}
          >
            {t('command_view', language)}
          </button>
          <button
            onClick={() => setActiveView('colony')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
              background: activeView === 'colony' ? '#0284c7' : '#1e293b',
              color: activeView === 'colony' ? '#ffffff' : '#94a3b8',
            }}
          >
            {t('colony_view', language)}
          </button>
        </div>

        {/* Language Toggle */}
        <button
          onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')}
          style={{
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            background: '#334155',
            color: '#f8fafc',
          }}
        >
          {language === 'hi' ? 'English' : 'हिंदी'}
        </button>
      </nav>

      {/* Main View Area */}
      <main style={{ flex: 1, overflow: 'hidden' }}>
        {activeView === 'command' ? <CommandView /> : <ColonyView />}
      </main>
    </div>
  );
};
