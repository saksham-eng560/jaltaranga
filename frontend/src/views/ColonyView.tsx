import React from 'react';
import { TimelineScrubber } from '../components/TimelineScrubber';
import { useReplayStore } from '../state/replay';
import { COLONIES, formatTimeToWater, hoursToWater, REPLAY_STEPS, riskForColony } from '../shared/mockData';
import { HELPLINE } from '../shared/constants';
import { t } from '../i18n/t';

export const ColonyView: React.FC = () => {
  const { language, selectedColonyId, setSelectedColonyId, currentTimestamp } = useReplayStore();
  const colony = COLONIES.find((item) => item.id === selectedColonyId) ?? COLONIES[0];
  const stage = REPLAY_STEPS.find((step) => step.timestamp === currentTimestamp) ?? REPLAY_STEPS[2];
  const risk = riskForColony(stage.level, colony.wetLevelM);
  const hours = hoursToWater(stage.level, colony.wetLevelM);
  const name = language === 'hi' ? colony.nameHi : colony.name;

  const listen = () => {
    const message =
      language === 'hi'
        ? `${colony.nameHi} में पानी ${formatTimeToWater(hours, language)} में पहुंच सकता है। ${colony.routeHi} से ${colony.shelterHi} जाएं। ${colony.avoidRoadHi} से बचें।`
        : `Water may reach ${colony.name} in ${formatTimeToWater(hours, language)}. Take ${colony.route} to ${colony.shelter}. Avoid ${colony.avoidRoad}.`;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="colony-view">
      <div className="colony-page-heading">
        <div>
          <p className="eyebrow">{language === 'hi' ? 'नागरिक जानकारी · डेमो रीप्ले' : 'RESIDENT INFORMATION · DEMO REPLAY'}</p>
          <h1>{language === 'hi' ? 'आपकी गली। आपका सुरक्षित रास्ता।' : 'Your street. A safer way forward.'}</h1>
        </div>
        <label className="colony-select-wrap">
          <span className="eyebrow">{language === 'hi' ? 'अपना क्षेत्र चुनें' : 'SELECT YOUR AREA'}</span>
          <select value={colony.id} onChange={(event) => setSelectedColonyId(event.currentTarget.value)}>
            {COLONIES.map((item) => (
              <option key={item.id} value={item.id}>{language === 'hi' ? item.nameHi : item.name}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="resident-card">
        <section className={`resident-alert risk-${risk}`}>
          <div className="resident-alert-top">
            <span className="eyebrow">{language === 'hi' ? 'आपका इलाका' : 'YOUR AREA'}</span>
            <span className={`risk-label risk-label-${risk}`}>
              {risk === 'critical'
                ? (language === 'hi' ? 'तत्काल कार्रवाई' : 'ACT NOW')
                : risk === 'watch'
                  ? (language === 'hi' ? 'नज़र रखें' : 'STAY ALERT')
                  : (language === 'hi' ? 'अभी सुरक्षित' : 'CURRENTLY SAFE')}
            </span>
          </div>
          <h2>{name}</h2>
          <div className="resident-countdown">
            <span>{t('time_to_water', language)}</span>
            <strong>{formatTimeToWater(hours, language)}</strong>
            <span>{language === 'hi' ? `अनुमानित जल स्तर ${colony.wetLevelM.toFixed(2)} m` : `Estimated water threshold ${colony.wetLevelM.toFixed(2)} m`}</span>
          </div>
          <div className="resident-level">
            <span>{language === 'hi' ? 'वर्तमान रीप्ले स्तर' : 'REPLAY WATER LEVEL'}</span>
            <strong>{stage.level.toFixed(2)} <small>m</small></strong>
            <span>{language === 'hi' ? stage.label : stage.label}</span>
          </div>
        </section>

        <section className="resident-instructions">
          <div className="instruction-block">
            <span className="instruction-number">01</span>
            <div>
              <span className="eyebrow">{t('safe_evac_route', language)}</span>
              <strong>{language === 'hi' ? colony.routeHi : colony.route}</strong>
              <span className="avoid-line">{language === 'hi' ? `इस सड़क से बचें: ${colony.avoidRoadHi}` : `Do not use: ${colony.avoidRoad}`}</span>
            </div>
          </div>
          <div className="instruction-block">
            <span className="instruction-number">02</span>
            <div>
              <span className="eyebrow">{t('shelter_destination', language)}</span>
              <strong>{language === 'hi' ? colony.shelterHi : colony.shelter}</strong>
              <span>{colony.freeBeds.toLocaleString('en-IN')} {t('free_beds', language)} · {language === 'hi' ? 'डेमो क्षमता' : 'sample capacity'}</span>
            </div>
          </div>
          <div className="resident-actions">
            <button className="button-primary resident-listen" onClick={listen} disabled={!('speechSynthesis' in window)}>
              <span aria-hidden="true">◖</span>{t('listen_audio', language)}
            </button>
            <a className="button-secondary" href={`tel:${HELPLINE.DISASTER_CONTROL}`}>
              {t('call_helpline', language)} <strong>{HELPLINE.DISASTER_CONTROL}</strong>
              <span aria-hidden="true">↗</span>
            </a>
          </div>
          <p className="resident-note">
            {language === 'hi'
              ? 'यह 2023 बाढ़ पर आधारित डेमो रीप्ले है। यह लाइव चेतावनी या व्यक्तिगत निकासी आदेश नहीं है।'
              : 'This is a demo replay based on the 2023 flood. It is not a live warning or a personal evacuation order.'}
          </p>
        </section>
      </div>

      <TimelineScrubber />
    </div>
  );
};
