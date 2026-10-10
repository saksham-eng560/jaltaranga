import React from 'react';
import { useReplayStore } from './state/replay';
import { CommandView } from './views/CommandView';
import { ColonyView } from './views/ColonyView';
import { t } from './i18n/t';

export const App: React.FC = () => {
  const { activeView, setActiveView, language, setLanguage } = useReplayStore();

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#" aria-label="Jaltaranga home">
          <span className="brand-mark" aria-hidden="true">J</span>
          <span className="brand-wordmark">
            <strong>जलतरंग</strong>
            <span>JALTARANGA / DELHI</span>
          </span>
        </a>

        <nav className="view-switcher" aria-label="Choose dashboard view">
          <button
            className={activeView === 'command' ? 'view-tab is-active' : 'view-tab'}
            onClick={() => setActiveView('command')}
            aria-current={activeView === 'command' ? 'page' : undefined}
          >
            <span className="tab-index">01</span>
            {t('command_view', language)}
          </button>
          <button
            className={activeView === 'colony' ? 'view-tab is-active' : 'view-tab'}
            onClick={() => setActiveView('colony')}
            aria-current={activeView === 'colony' ? 'page' : undefined}
          >
            <span className="tab-index">02</span>
            {t('colony_view', language)}
          </button>
        </nav>

        <div className="header-actions">
          <span className="replay-indicator">
            <span className="status-dot" />
            {language === 'hi' ? 'डेमो रीप्ले' : 'DEMO REPLAY'}
          </span>
          <button
            className="language-button"
            onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')}
            aria-label={language === 'hi' ? 'Switch to English' : 'हिंदी में बदलें'}
          >
            {language === 'hi' ? 'EN' : 'हि'}
            <span aria-hidden="true">↗</span>
          </button>
        </div>
      </header>

      <main className="app-main">
        {activeView === 'command' ? <CommandView /> : <ColonyView />}
      </main>
    </div>
  );
};
