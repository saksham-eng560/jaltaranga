import React, { useEffect, useState } from 'react';
import { t } from '../i18n/t';
import { useReplayStore } from '../state/replay';
import { ColonyScenario } from '../shared/mockData';

interface DispatchCardProps {
  colony: ColonyScenario;
}

export const DispatchCardView: React.FC<DispatchCardProps> = ({ colony }) => {
  const { language } = useReplayStore();
  const [status, setStatus] = useState<'draft' | 'approved' | 'sent'>('draft');
  const colonyName = language === 'hi' ? colony.nameHi : colony.name;
  const route = language === 'hi' ? colony.routeHi : colony.route;
  const avoidRoad = language === 'hi' ? colony.avoidRoadHi : colony.avoidRoad;
  const message =
    language === 'hi'
      ? `बाढ़ सूचना: ${colonyName} में पानी बढ़ने का अनुमान है। कृपया ${route} से ${colony.shelterHi} जाएं। ${avoidRoad} से बचें। आपातकालीन हेल्पलाइन 1077।`
      : `Flood advisory: Water is expected to rise near ${colonyName}. Please use ${route} to reach ${colony.shelter}. Avoid ${avoidRoad}. Emergency helpline: 1077.`;

  useEffect(() => {
    setStatus('draft');
  }, [colony.id]);

  const listen = () => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
    window.speechSynthesis.speak(utterance);
  };

  return (
    <section className="dispatch-card">
      <div className="dispatch-heading">
        <div>
          <span className="eyebrow">{language === 'hi' ? 'संदेश पूर्वावलोकन' : 'MESSAGE PREVIEW'}</span>
          <h3>{t('draft_dispatch', language)}</h3>
        </div>
        <span className={`dispatch-status status-${status}`}>
          {status === 'draft'
            ? (language === 'hi' ? 'ड्राफ्ट' : 'DRAFT')
            : status === 'approved'
              ? (language === 'hi' ? 'स्वीकृत' : 'APPROVED')
              : (language === 'hi' ? 'भेजा गया · डेमो' : 'SENT · DEMO')}
        </span>
      </div>

      <p className="dispatch-message">{message}</p>

      <div className="validation-row">
        <span><i aria-hidden="true">✓</i> {language === 'hi' ? 'तथ्य जांच' : 'Facts checked'}</span>
        <span><i aria-hidden="true">✓</i> {language === 'hi' ? 'हिंदी + अंग्रेज़ी' : 'Hindi + English'}</span>
      </div>

      <div className="dispatch-actions">
        {status === 'draft' && (
          <button className="button-primary" onClick={() => setStatus('approved')}>
            {language === 'hi' ? 'ड्राफ्ट स्वीकृत करें' : 'Approve draft'}
            <span aria-hidden="true">↗</span>
          </button>
        )}
        {status === 'approved' && (
          <button className="button-primary" onClick={() => setStatus('sent')}>
            {language === 'hi' ? 'भेजने का डेमो चलाएं' : 'Simulate sending'}
            <span aria-hidden="true">↗</span>
          </button>
        )}
        {status === 'sent' && (
          <span className="sent-confirmation">
            {language === 'hi' ? 'केवल इस डेमो में चिह्नित · कोई अलर्ट नहीं भेजा गया' : 'Marked in this demo only · no alert was sent'}
          </span>
        )}
        <button
          className="button-listen"
          onClick={listen}
          disabled={!('speechSynthesis' in window)}
          title={!('speechSynthesis' in window) ? 'Speech playback is not available in this browser' : undefined}
        >
          <span aria-hidden="true">◖</span>
          {t('listen_audio', language)}
        </button>
      </div>
    </section>
  );
};
