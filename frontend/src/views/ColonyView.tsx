import React from 'react';
import { useReplayStore } from '../state/replay';
import { t } from '../i18n/t';
import { HELPLINE } from '../shared/constants';

export const ColonyView: React.FC = () => {
  const { language, setLanguage } = useReplayStore();

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        background: '#0f172a',
        color: '#f8fafc',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '16px',
      }}
    >
      {/* Mobile Header */}
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h1 style={{ fontSize: '1.2rem', color: '#38bdf8' }}>जलतरंग (Jaltaranga)</h1>
        <button
          onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')}
          style={{
            background: '#334155',
            color: '#f8fafc',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.8rem',
          }}
        >
          {language === 'hi' ? 'English' : 'हिंदी'}
        </button>
      </div>

      {/* Main Resident Card */}
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          background: '#1e293b',
          borderRadius: '16px',
          border: '2px solid #ef4444',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div>
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>आपका इलाका (Your Location)</span>
          <h2 style={{ fontSize: '1.6rem', color: '#ffffff', fontWeight: 800 }}>
            {language === 'hi' ? 'यमुना पुश्ता (सेक्टर सी)' : 'Yamuna Pushta (Sector C)'}
          </h2>
        </div>

        {/* Big Alert Banner */}
        <div
          style={{
            background: '#450a0a',
            border: '1px solid #b91c1c',
            padding: '16px',
            borderRadius: '12px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '0.9rem', color: '#fca5a5' }}>{t('time_to_water', language)}</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: '#ef4444', margin: '4px 0' }}>
            ~3½ घंटे (3.5 h)
          </div>
          <div style={{ fontSize: '0.85rem', color: '#f87171' }}>
            अनुमानित जलभराव: 206.3 मीटर (Your lane floods at 206.3 m)
          </div>
        </div>

        {/* Route Instruction */}
        <div style={{ background: '#0f172a', padding: '14px', borderRadius: '10px' }}>
          <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: '4px' }}>
            🛣️ {t('safe_evac_route', language)}
          </div>
          <div style={{ fontSize: '1rem', color: '#e2e8f0', lineHeight: 1.4 }}>
            {language === 'hi'
              ? 'लाल कुआं मार्ग होकर सीधे कश्मीरी गेट राहत शिविर की ओर जाएं।'
              : 'Proceed via Lal Kuan Marg directly towards Kashmere Gate Shelter.'}
          </div>
          <div
            style={{
              marginTop: '8px',
              padding: '6px 10px',
              borderRadius: '6px',
              background: '#7f1d1d',
              color: '#fecaca',
              fontSize: '0.8rem',
              fontWeight: 600,
            }}
          >
            ❌ {t('avoid_warning', language)}
          </div>
        </div>

        {/* Shelter Destination */}
        <div style={{ background: '#0f172a', padding: '14px', borderRadius: '10px' }}>
          <div style={{ fontWeight: 700, color: '#10b981', marginBottom: '4px' }}>
            🏕️ {t('shelter_destination', language)}
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
            ISBT कम्युनिटी सेंटर राहत शिविर #2
          </div>
          <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '2px' }}>
            उपलब्ध बिस्तर (Free beds): 480 · भोजन एवं प्राथमिक चिकित्सा उपलब्ध
          </div>
        </div>

        {/* Offline Audio and Emergency Call Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button
            onClick={() => {
              const msg =
                language === 'hi'
                  ? 'चेतावनी: यमुना पुश्ता सेक्टर सी में लगभग साढ़े तीन घंटे में पानी भरने की संभावना है। कृपया लाल कुआं मार्ग से राहत शिविर जाएं। रिंग रोड न लें।'
                  : 'Warning: Yamuna Pushta Sector C is expected to submerge in 3.5 hours. Please proceed via Lal Kuan Marg to relief shelter. Do not take Ring Road.';
              const utterance = new SpeechSynthesisUtterance(msg);
              utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
              window.speechSynthesis.speak(utterance);
            }}
            style={{
              padding: '14px',
              borderRadius: '10px',
              background: '#0284c7',
              color: '#ffffff',
              fontSize: '1.05rem',
              fontWeight: 700,
            }}
          >
            🔊 {t('listen_audio', language)}
          </button>

          <a
            href={`tel:${HELPLINE.DISASTER_CONTROL}`}
            style={{
              padding: '14px',
              borderRadius: '10px',
              background: '#dc2626',
              color: '#ffffff',
              fontSize: '1.05rem',
              fontWeight: 700,
              textAlign: 'center',
              textDecoration: 'none',
            }}
          >
            📞 {t('call_helpline', language)} ({HELPLINE.DISASTER_CONTROL} / {HELPLINE.POLICE_EMERGENCY})
          </a>
        </div>
      </div>
    </div>
  );
};
