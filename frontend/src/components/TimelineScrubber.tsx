import React, { useEffect } from 'react';
import { useReplayStore } from '../state/replay';
import { REPLAY_STEPS } from '../shared/mockData';

export const TimelineScrubber: React.FC = () => {
  const { currentTimestamp, setCurrentTimestamp, isPlaying, setIsPlaying, language } = useReplayStore();
  const currentIndex = Math.max(0, REPLAY_STEPS.findIndex((step) => step.timestamp === currentTimestamp));
  const activeStep = REPLAY_STEPS[currentIndex];

  useEffect(() => {
    if (!isPlaying) return undefined;

    const timer = window.setInterval(() => {
      const nextIndex = REPLAY_STEPS.findIndex((step) => step.timestamp === currentTimestamp) + 1;
      if (nextIndex >= REPLAY_STEPS.length) {
        setIsPlaying(false);
        return;
      }
      setCurrentTimestamp(REPLAY_STEPS[nextIndex].timestamp);
    }, 1400);

    return () => window.clearInterval(timer);
  }, [currentTimestamp, isPlaying, setCurrentTimestamp, setIsPlaying]);

  const moveToStep = (index: number) => {
    setCurrentTimestamp(REPLAY_STEPS[index].timestamp);
    if (index === REPLAY_STEPS.length - 1) setIsPlaying(false);
  };

  return (
    <section className="timeline-panel" aria-label={language === 'hi' ? 'ऐतिहासिक बाढ़ रीप्ले' : 'Historical flood replay'}>
      <div className="timeline-topline">
        <div className="timeline-title">
          <span className="timeline-symbol" aria-hidden="true">↗</span>
          <div>
            <span className="eyebrow">{language === 'hi' ? 'रीप्ले कंट्रोल' : 'REPLAY CONTROL'}</span>
            <strong>{language === 'hi' ? 'जुलाई 2023 · यमुना बाढ़' : 'July 2023 · Yamuna flood'}</strong>
          </div>
        </div>
        <div className="timeline-current">
          <span>{activeStep.label}</span>
          <strong>{activeStep.level.toFixed(2)} <small>m</small></strong>
        </div>
        <button
          className="play-button"
          onClick={() => {
            if (currentIndex === REPLAY_STEPS.length - 1) moveToStep(0);
            setIsPlaying(!isPlaying);
          }}
          aria-pressed={isPlaying}
        >
          <span aria-hidden="true">{isPlaying ? 'Ⅱ' : '▶'}</span>
          {isPlaying
            ? (language === 'hi' ? 'रोकें' : 'Pause')
            : (language === 'hi' ? 'रीप्ले चलाएं' : 'Play replay')}
        </button>
      </div>

      <div className="timeline-control">
        <span className="timeline-end">{language === 'hi' ? '12 जुलाई' : '12 JUL'}</span>
        <input
          type="range"
          min={0}
          max={REPLAY_STEPS.length - 1}
          step={1}
          value={currentIndex}
          onChange={(event) => moveToStep(Number(event.currentTarget.value))}
          aria-label={language === 'hi' ? 'रीप्ले समय चुनें' : 'Choose replay time'}
          aria-valuetext={`${activeStep.label}, ${activeStep.level.toFixed(2)} metres`}
        />
        <span className="timeline-end">{language === 'hi' ? '13 जुलाई' : '13 JUL'}</span>
      </div>

      <div className="timeline-stops" role="group" aria-label={language === 'hi' ? 'रीप्ले चरण' : 'Replay steps'}>
        {REPLAY_STEPS.map((step, index) => (
          <button
            key={step.timestamp}
            className={index === currentIndex ? 'timeline-stop is-current' : 'timeline-stop'}
            onClick={() => moveToStep(index)}
            aria-pressed={index === currentIndex}
          >
            <span className="stop-marker" />
            <span>{step.label.slice(7)}</span>
          </button>
        ))}
      </div>
    </section>
  );
};
