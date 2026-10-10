import React from 'react';
import { MapView } from '../map/MapView';
import { TimelineScrubber } from '../components/TimelineScrubber';
import { DispatchCardView } from '../components/DispatchCard';
import { useReplayStore } from '../state/replay';
import { t } from '../i18n/t';
import { COLONIES, formatTimeToWater, hoursToWater, REPLAY_STEPS, riskForColony } from '../shared/mockData';

export const CommandView: React.FC = () => {
  const { selectedColonyId, setSelectedColonyId, currentTimestamp, language } = useReplayStore();
  const stage = REPLAY_STEPS.find((step) => step.timestamp === currentTimestamp) ?? REPLAY_STEPS[2];
  const selectedColony = COLONIES.find((colony) => colony.id === selectedColonyId) ?? COLONIES[0];
  const atRisk = COLONIES.filter((colony) => riskForColony(stage.level, colony.wetLevelM) !== 'safe');
  const peopleAtRisk = atRisk.reduce((total, colony) => total + colony.population, 0);
  const criticalCount = COLONIES.filter(
    (colony) => riskForColony(stage.level, colony.wetLevelM) === 'critical',
  ).length;
  const risk = riskForColony(stage.level, selectedColony.wetLevelM);
  const hours = (selectedColony.wetLevelM - stage.level) / 0.06;
  const name = language === 'hi' ? selectedColony.nameHi : selectedColony.name;

  return (
    <div className="command-view">
      <section className="command-intro">
        <div>
          <p className="eyebrow">{language === 'hi' ? 'दिल्ली · यमुना कॉरिडोर' : 'DELHI · YAMUNA CORRIDOR'}</p>
          <h1>
            {language === 'hi' ? (
              <>नदी को पढ़ें। <span>हर गली को सुरक्षित करें।</span></>
            ) : (
              <>Read the river.<br className="desktop-break" /> <span>Protect every street.</span></>
            )}
          </h1>
        </div>
        <div className="intro-note">
          <span className="eyebrow">{language === 'hi' ? 'ऐतिहासिक परिदृश्य' : 'HISTORICAL SCENARIO'}</span>
          <strong>{language === 'hi' ? 'यमुना बाढ़ · जुलाई 2023' : 'Yamuna flood · July 2023'}</strong>
          <span>{language === 'hi' ? 'डेमो डेटा · लाइव चेतावनी नहीं' : 'Sample replay data · not a live alert'}</span>
        </div>
      </section>

      <section className="summary-strip" aria-label="Replay overview">
        <div className="summary-item">
          <span className="summary-label">{language === 'hi' ? 'नदी का स्तर' : 'RIVER LEVEL'}</span>
          <strong>{stage.level.toFixed(2)} <small>m</small></strong>
          <span className="summary-caption">Delhi Railway Bridge</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">{language === 'hi' ? 'जोखिम में क्षेत्र' : 'AREAS AT RISK'}</span>
          <strong>{atRisk.length.toString().padStart(2, '0')} <small>/ {COLONIES.length.toString().padStart(2, '0')}</small></strong>
          <span className="summary-caption">{criticalCount} {language === 'hi' ? 'तत्काल' : 'critical now'}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">{language === 'hi' ? 'प्रभावित आबादी' : 'PEOPLE IN AT-RISK AREAS'}</span>
          <strong>{peopleAtRisk.toLocaleString('en-IN')}</strong>
          <span className="summary-caption">{language === 'hi' ? 'चार कॉलोनियों का डेमो' : 'Across the demo colonies'}</span>
        </div>
        <div className="summary-item summary-asof">
          <span className="summary-label">{language === 'hi' ? 'रीप्ले समय' : 'REPLAYING'}</span>
          <strong>{stage.label}</strong>
          <span className="summary-caption">{language === 'hi' ? 'जुलाई 2023 का ऐतिहासिक रीप्ले' : 'Historical replay · July 2023'}</span>
        </div>
      </section>

      <section className="command-workspace">
        <aside className="workspace-panel queue-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{language === 'hi' ? 'प्राथमिकता सूची' : 'FIELD PRIORITIES'}</p>
              <h2>{language === 'hi' ? 'निकासी कतार' : 'Evacuation queue'}</h2>
            </div>
            <span className="count-pill">{atRisk.length.toString().padStart(2, '0')}</span>
          </div>

          <div className="colony-list">
            {COLONIES.map((colony, index) => {
              const colonyRisk = riskForColony(stage.level, colony.wetLevelM);
              const isSelected = colony.id === selectedColony.id;
              return (
                <button
                  className={`colony-row risk-${colonyRisk}${isSelected ? ' is-selected' : ''}`}
                  key={colony.id}
                  onClick={() => setSelectedColonyId(colony.id)}
                  aria-pressed={isSelected}
                >
                  <span className="queue-rank">{String(index + 1).padStart(2, '0')}</span>
                  <span className="queue-copy">
                    <strong>{language === 'hi' ? colony.nameHi : colony.name}</strong>
                    <span>{colony.population.toLocaleString('en-IN')} {language === 'hi' ? 'निवासी' : 'residents'}</span>
                  </span>
                  <span className="queue-time">
                    <span className="risk-dot" />
                    {formatTimeToWater(hoursToWater(stage.level, colony.wetLevelM), language)}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="road-alert">
            <span className="alert-mark" aria-hidden="true">!</span>
            <div>
              <strong>{language === 'hi' ? 'सड़क बंद · 0.30 m सीमा' : 'Road cutoff · 0.30 m limit'}</strong>
              <span>{language === 'hi' ? 'रिंग रोड से बचें। लाल कुआं मार्ग खुला है।' : 'Avoid Ring Road. Lal Kuan Marg remains open.'}</span>
            </div>
          </div>
        </aside>

        <section className="workspace-panel map-panel" aria-label="Yamuna corridor map">
          <div className="map-heading">
            <div>
              <p className="eyebrow">{language === 'hi' ? 'क्षेत्रीय दृश्य' : 'SITUATION MAP'}</p>
              <h2>{language === 'hi' ? 'यमुना कॉरिडोर' : 'Yamuna corridor'}</h2>
            </div>
            <span className="map-live-label"><span className="status-dot" /> {language === 'hi' ? 'रीप्ले' : 'REPLAY'}</span>
          </div>
          <div className="map-canvas">
            <MapView
              selectedColonyId={selectedColony.id}
              stageLevel={stage.level}
              onSelectColony={setSelectedColonyId}
            />
            <div className="map-credit">{language === 'hi' ? 'दिल्ली · अनुमानित क्षेत्र' : 'DELHI · APPROXIMATE AREA'}</div>
          </div>
          <div className="map-legend">
            <span><i className="legend-dot legend-critical" /> {language === 'hi' ? 'तत्काल' : 'Critical'}</span>
            <span><i className="legend-dot legend-watch" /> {language === 'hi' ? 'निगरानी' : 'Watch'}</span>
            <span><i className="legend-dot legend-safe" /> {language === 'hi' ? 'सुरक्षित' : 'Safe'}</span>
            <span className="legend-source">{language === 'hi' ? 'नक्शा: OpenStreetMap' : 'Map data © OpenStreetMap'}</span>
          </div>
        </section>

        <aside className="workspace-panel detail-panel">
          <div className="panel-heading detail-heading">
            <div>
              <p className="eyebrow">{language === 'hi' ? 'चयनित कॉलोनी' : 'SELECTED COLONY'}</p>
              <h2>{name}</h2>
            </div>
            <span className={`risk-label risk-label-${risk}`}>
              {risk === 'critical'
                ? (language === 'hi' ? 'तत्काल' : 'CRITICAL')
                : risk === 'watch'
                  ? (language === 'hi' ? 'निगरानी' : 'WATCH')
                  : (language === 'hi' ? 'सुरक्षित' : 'SAFE')}
            </span>
          </div>

          <div className="detail-stats">
            <div className="detail-stat">
              <span>{t('time_to_water', language)}</span>
              <strong className={`time-value text-${risk}`}>{formatTimeToWater(Math.max(0, hours), language)}</strong>
              <small>{language === 'hi' ? `जलभराव ${selectedColony.wetLevelM.toFixed(2)} m पर` : `Wet threshold ${selectedColony.wetLevelM.toFixed(2)} m`}</small>
            </div>
            <div className="detail-stat">
              <span>{language === 'hi' ? 'आबादी' : 'RESIDENTS'}</span>
              <strong>{selectedColony.population.toLocaleString('en-IN')}</strong>
              <small>{language === 'hi' ? 'डेमो कॉलोनी डेटा' : 'Illustrative sample'}</small>
            </div>
          </div>

          <div className="route-block">
            <span className="eyebrow">{t('safe_evac_route', language)}</span>
            <strong>{language === 'hi' ? selectedColony.routeHi : selectedColony.route}</strong>
            <span className="avoid-line">
              {language === 'hi' ? `बचें: ${selectedColony.avoidRoadHi}` : `AVOID · ${selectedColony.avoidRoad}`}
            </span>
          </div>

          <div className="shelter-block">
            <div>
              <span className="eyebrow">{t('shelter_destination', language)}</span>
              <strong>{language === 'hi' ? selectedColony.shelterHi : selectedColony.shelter}</strong>
            </div>
            <span className="bed-count">
              <strong>{selectedColony.freeBeds.toLocaleString('en-IN')}</strong>
              <small>{t('free_beds', language)}</small>
            </span>
          </div>

          <DispatchCardView colony={selectedColony} />
        </aside>
      </section>

      <TimelineScrubber />
    </div>
  );
}
