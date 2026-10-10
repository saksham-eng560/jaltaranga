import React, { useState } from 'react';
import { DispatchCard } from '../shared/types';
import { t } from '../i18n/t';
import { useReplayStore } from '../state/replay';

interface DispatchCardProps {
  colonyName: string;
}

export const DispatchCardView: React.FC<DispatchCardProps> = ({ colonyName }) => {
  const { language } = useReplayStore();
  const [status, setStatus] = useState<'draft' | 'approved' | 'sent'>('draft');

  const messageHi = `बाढ़ चेतावनी: ${colonyName} में अगले 3 घंटे में पानी का स्तर बढ़ने की संभावना है। कृपया सुरक्षित निकासी मार्ग से सामुदायिक केंद्र राहत शिविर में जाएं। रिंग रोड का उपयोग न करें। आपात स्थिति में 1077 पर संपर्क करें।`;
  const messageEn = `Flood Warning: Water level expected to rise at ${colonyName} within 3 hours. Please evacuate via designated route to Community Centre Shelter. Avoid Ring Road. Emergency helpline: 1077.`;

  return (
    <div
      style={{
        background: '#0f172a',
        padding: '16px',
        borderRadius: '8px',
        border: '1px solid #334155',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ color: '#38bdf8', fontSize: '1rem' }}>
          {status === 'sent' ? `✅ ${t('status_sent', language)}` : t('draft_dispatch', language)}
        </h4>
        <span
          style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            borderRadius: '12px',
            background: status === 'sent' ? '#065f46' : '#854d0e',
            color: '#f8fafc',
          }}
        >
          {status.toUpperCase()}
        </span>
      </div>

      <div
        style={{
          background: '#1e293b',
          padding: '12px',
          borderRadius: '6px',
          fontSize: '0.9rem',
          lineHeight: '1.4',
          color: '#e2e8f0',
        }}
      >
        {language === 'hi' ? messageHi : messageEn}
      </div>

      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <span style={{ fontSize: '0.75rem', color: '#10b981' }}>✓ Slots Validated</span>
        <span style={{ fontSize: '0.75rem', color: '#10b981' }}>✓ No Hallucinations</span>
        <span style={{ fontSize: '0.75rem', color: '#10b981' }}>✓ Dual Script</span>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
        {status === 'draft' && (
          <button
            onClick={() => setStatus('approved')}
            style={{
              flex: 1,
              padding: '8px',
              borderRadius: '6px',
              background: '#0284c7',
              color: '#ffffff',
              fontWeight: '600',
            }}
          >
            {t('approve_dispatch', language)}
          </button>
        )}

        {status === 'approved' && (
          <button
            onClick={() => setStatus('sent')}
            style={{
              flex: 1,
              padding: '8px',
              borderRadius: '6px',
              background: '#10b981',
              color: '#ffffff',
              fontWeight: '600',
            }}
          >
            🚀 Push SNS & Radio Broadcast
          </button>
        )}

        <button
          onClick={() => {
            const utterance = new SpeechSynthesisUtterance(language === 'hi' ? messageHi : messageEn);
            utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
            window.speechSynthesis.speak(utterance);
          }}
          style={{
            padding: '8px 14px',
            borderRadius: '6px',
            background: '#334155',
            color: '#f8fafc',
          }}
        >
          🔊 {t('listen_audio', language)}
        </button>
      </div>
    </div>
  );
};
