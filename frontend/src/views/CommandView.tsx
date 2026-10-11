import { useCallback, useEffect, useState } from 'react';
import type { DispatchCard, ReplayStep } from '../shared/types';
import { FloodResponseMap } from '../components/FloodResponseMap';
import { Icon } from '../components/Shared';
import { TIMELINE_STEPS, type ReplayTimelineStep } from '../data/floodScenarioData';

interface CommandViewProps {
  step: ReplayStep;
  selectedColony: string;
  onSelectColony: (id: string) => void;
  onApproved: (card: DispatchCard) => void;
  onNavigate?: (view: 'command' | 'colony' | 'compare' | 'report') => void;
}

export function CommandView({
  selectedColony,
  onSelectColony,
  onApproved: _onApproved,
  onNavigate,
}: CommandViewProps) {
  // Default to step 2 (JUN 17 16:00 peak flood, which is the canonical view in the user's screenshot)
  const [activeStepIndex, setActiveStepIndex] = useState(2);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [scrubberValue, setScrubberValue] = useState(2);

  const currentTimelineStep: ReplayTimelineStep = TIMELINE_STEPS[activeStepIndex] || TIMELINE_STEPS[2];

  // Speech Audio Synthesis for "Play Dispatch Audio"
  const handlePlayAudio = useCallback(() => {
    if (isPlayingAudio) {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
      return;
    }

    setIsPlayingAudio(true);

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();

      // First speak English announcement
      const englishUtterance = new SpeechSynthesisUtterance(currentTimelineStep.dispatch.messageEn);
      englishUtterance.lang = 'en-IN';
      englishUtterance.rate = 0.95;

      // Then speak Hindi announcement
      const hindiUtterance = new SpeechSynthesisUtterance(currentTimelineStep.dispatch.messageHi);
      hindiUtterance.lang = 'hi-IN';
      hindiUtterance.rate = 0.9;

      englishUtterance.onend = () => {
        window.speechSynthesis.speak(hindiUtterance);
      };

      hindiUtterance.onend = () => {
        setIsPlayingAudio(false);
      };

      hindiUtterance.onerror = () => {
        setIsPlayingAudio(false);
      };

      window.speechSynthesis.speak(englishUtterance);
    } else {
      // Fallback: Web Audio tone chime if speech synthesis is not supported
      try {
        const win = window as unknown as Record<string, new () => AudioContext>;
        const AudioCtx = win.AudioContext || win.webkitAudioContext;
        if (!AudioCtx) throw new Error('AudioContext unavailable');
        const audioCtx = new AudioCtx();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
        osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.2); // A5
        gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 1.2);
        osc.start();
        osc.stop(audioCtx.currentTime + 1.2);
        setTimeout(() => setIsPlayingAudio(false), 1200);
      } catch {
        setTimeout(() => setIsPlayingAudio(false), 1000);
      }
    }
  }, [isPlayingAudio, currentTimelineStep]);

  // Clean up speech synthesis on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleStepSelect = (index: number) => {
    setActiveStepIndex(index);
    setScrubberValue(index);
  };

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setScrubberValue(val);
    const closestIndex = Math.min(Math.max(Math.round(val), 0), TIMELINE_STEPS.length - 1);
    setActiveStepIndex(closestIndex);
  };

  return (
    <div className="command-center-root">
      {/* Top Application Header */}
      <header className="command-header">
        <div className="header-brand">
          <div className="brand-logo-icon">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2.5C12 2.5 4.5 11 4.5 16C4.5 20.14 7.86 23.5 12 23.5C16.14 23.5 19.5 20.14 19.5 16C19.5 11 12 2.5 12 2.5Z"
                fill="#38bdf8"
                opacity="0.85"
              />
              <path
                d="M12 6C12 6 7 12.5 7 16.5C7 19.54 9.46 22 12.5 22C15.54 22 18 19.54 18 16.5C18 12.5 12 6 12 6Z"
                fill="#0284c7"
              />
              <path
                d="M11 14C11 14 9.5 16 9.5 17.5C9.5 18.88 10.62 20 12 20"
                stroke="#ffffff"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <span className="brand-title">JALTARANGA</span>
        </div>

        <div className="header-meta">
          <span className="header-datetime">{currentTimelineStep.dateTimeDisplay}</span>
          <div className="header-system-status">
            System Status: <strong>ACTIVE</strong>
          </div>
        </div>
      </header>

      {/* Main Body: Left Vertical Icon Rail + 3 Column Dashboard Content */}
      <div className="command-body">
        {/* Far-Left Vertical Icon Rail */}
        <aside className="command-sidebar-icons" aria-label="System navigation">
          <div className="sidebar-icons-top">
            <button
              className="sidebar-icon-btn active"
              title="Flood Response Command Center"
              onClick={() => onNavigate?.('command')}
              aria-label="Command Center"
            >
              <Icon name="grid" size={20} />
            </button>
            <button
              className="sidebar-icon-btn"
              title="Resident Colony View"
              onClick={() => onNavigate?.('colony')}
              aria-label="Citizen Colony View"
            >
              <Icon name="home" size={20} />
            </button>
            <button
              className="sidebar-icon-btn"
              title="Active Alerts"
              onClick={() => onNavigate?.('command')}
              aria-label="Alerts"
            >
              <Icon name="alert" size={20} />
            </button>
            <button
              className="sidebar-icon-btn"
              title="Community & Relief Marshals"
              onClick={() => onNavigate?.('colony')}
              aria-label="Community"
            >
              <Icon name="users" size={20} />
            </button>
            <button
              className="sidebar-icon-btn"
              title="Scenario Compare & Data"
              onClick={() => onNavigate?.('compare')}
              aria-label="Data Compare"
            >
              <Icon name="folder" size={20} />
            </button>
            <button
              className="sidebar-icon-btn"
              title="System Settings"
              onClick={() => onNavigate?.('report')}
              aria-label="Settings"
            >
              <Icon name="settings" size={20} />
            </button>
          </div>

          <div className="sidebar-icons-bottom">
            <button
              className="sidebar-icon-btn"
              title="Help & System Documentation"
              onClick={() => onNavigate?.('report')}
              aria-label="Help"
            >
              <Icon name="help" size={20} />
            </button>
          </div>
        </aside>

        {/* 3-Column Dashboard Layout */}
        <main className="command-workspace">
          {/* COLUMN 1: EVACUATION QUEUE (Left Rail) */}
          <section className="command-left-rail" aria-label="Evacuation Queue">
            <div className="rail-panel queue-panel">
              <div className="rail-panel-header">
                <h2>EVACUATION QUEUE</h2>
              </div>

              {/* Column labels */}
              <div className="queue-header-row">
                <span className="col-rank">Rank</span>
                <span className="col-lead">Lead Time</span>
                <span className="col-pop">Population</span>
              </div>

              {/* Ranked Colony Cards */}
              <div className="queue-card-list" role="list">
                {currentTimelineStep.queue.map((item) => {
                  const isSelected = item.colonyId === selectedColony;
                  return (
                    <div
                      key={item.rank}
                      role="listitem"
                      tabIndex={0}
                      className={`queue-card card-accent-${item.alertTone} ${
                        isSelected ? 'card-selected' : ''
                      }`}
                      onClick={() => onSelectColony(item.colonyId)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          onSelectColony(item.colonyId);
                        }
                      }}
                      aria-pressed={isSelected}
                    >
                      <div className="card-badge-block">
                        <span className={`alert-badge badge-${item.alertTone}`}>ALERT</span>
                        <span className="rank-text">Rank</span>
                        <strong className="rank-number">{item.rank}</strong>
                      </div>

                      <div className="card-center-block">
                        <span className="field-label">Colony Name</span>
                        <strong className="colony-name-text">{item.colonyName}</strong>
                        <div className="lead-time-value">{item.leadTime}</div>
                      </div>

                      <div className="card-right-block">
                        <span className="field-label">Population</span>
                        <strong className="population-value">{item.population}</strong>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Amber Warning Box */}
              <div className="amber-warning-box">
                <div className="warning-box-title">{currentTimelineStep.warningBox.title}</div>
                <div className="warning-box-message">{currentTimelineStep.warningBox.message}</div>
              </div>
            </div>
          </section>

          {/* COLUMN 2: FLOOD RESPONSE MAP (Center) */}
          <section className="command-center-map" aria-label="Flood Response Map">
            <FloodResponseMap
              timelineStep={currentTimelineStep}
              selectedColonyId={selectedColony}
              onSelectColony={onSelectColony}
            />
          </section>

          {/* COLUMN 3: RIGHT RAIL (Details, Dispatch, Timeline Scrubber) */}
          <section className="command-right-rail" aria-label="Evacuation Plan Details & Dispatch">
            {/* Box 1: EVACUATION PLAN DETAILS */}
            <div className="rail-panel details-panel">
              <div className="rail-panel-header">
                <h2>EVACUATION PLAN DETAILS</h2>
              </div>

              <div className="plan-metrics-grid">
                <div className="metric-box">
                  <span className="metric-label">WATER LEVEL</span>
                  <div className="metric-value-row">
                    <span className="metric-main-value">{currentTimelineStep.waterLevel}</span>
                    <span className="metric-delta-value">
                      {currentTimelineStep.waterLevelDelta}
                    </span>
                  </div>
                </div>

                <div className="metric-box">
                  <span className="metric-label">DANGER</span>
                  <div className={`metric-danger-value danger-${currentTimelineStep.dangerTone}`}>
                    {currentTimelineStep.danger}
                  </div>
                </div>

                <div className="metric-box">
                  <span className="metric-label">AFFECTED POPULATION</span>
                  <div className="metric-main-value">{currentTimelineStep.affectedPopulation}</div>
                </div>

                <div className="metric-box">
                  <span className="metric-label">BOATS DEPLOYED</span>
                  <div className="metric-main-value">{currentTimelineStep.boatsDeployed}</div>
                </div>
              </div>
            </div>

            {/* Box 2: DISPATCH ALERT (प्रेषण अलर्ट) */}
            <div className="rail-panel dispatch-alert-panel">
              <div className="dispatch-header-bar">
                <span className="dispatch-title-en">DISPATCH ALERT</span>
                <span className="dispatch-title-hi">प्रेषण अलर्ट</span>
              </div>

              <div className="dispatch-card-content">
                <div className="dispatch-status-row">
                  <div className="status-label">Status</div>
                  <div className="status-value-approved">
                    <span>{currentTimelineStep.dispatch.status}</span>
                    <span className="check-circle-icon">✓</span>
                  </div>
                </div>

                <div className="dispatch-body-section">
                  <div className="body-label">Body</div>
                  <p className="body-en">{currentTimelineStep.dispatch.messageEn}</p>
                  <p className="body-hi" lang="hi">
                    {currentTimelineStep.dispatch.messageHi}
                  </p>
                </div>

                <button
                  className={`play-dispatch-audio-btn ${isPlayingAudio ? 'is-playing' : ''}`}
                  onClick={handlePlayAudio}
                  aria-label="Play Dispatch Audio"
                >
                  <span className="btn-audio-text">
                    {isPlayingAudio ? 'Playing Dispatch Audio…' : 'Play Dispatch Audio 🔊'}
                  </span>
                </button>
              </div>
            </div>

            {/* Box 3: TIMELINE REPLAY SCRUBBER */}
            <div className="rail-panel scrubber-panel">
              <div className="scrubber-header-row">
                <h2>TIMELINE REPLAY SCRUBBER</h2>
                <button className="scrubber-dots-btn" aria-label="Scrubber options">
                  <Icon name="dots" size={16} />
                </button>
              </div>

              {/* 4 Step Buttons */}
              <div className="scrubber-buttons-row">
                {TIMELINE_STEPS.map((s, idx) => (
                  <button
                    key={s.id}
                    className={`step-btn ${idx === activeStepIndex ? 'step-btn-active' : ''}`}
                    onClick={() => handleStepSelect(idx)}
                  >
                    {s.buttonLabel}
                  </button>
                ))}
              </div>

              {/* Slider Track */}
              <div className="scrubber-slider-container">
                <label className="sr-only" htmlFor="timeline-replay-slider">
                  Timeline scrubber
                </label>
                <input
                  id="timeline-replay-slider"
                  type="range"
                  min="0"
                  max={TIMELINE_STEPS.length - 1}
                  step="0.05"
                  value={scrubberValue}
                  onChange={handleScrubberChange}
                  className="timeline-slider-input"
                />
              </div>

              {/* Status Footer */}
              <div className="scrubber-footer-row">
                <span className="footer-water-level">
                  WATER LEVEL: <strong>{currentTimelineStep.scrubberWaterLevel}</strong>
                </span>
                <span className="footer-time">
                  TIME: <strong>{currentTimelineStep.scrubberTime}</strong>
                </span>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
