import { useEffect, useMemo } from 'react';
import { Icon, Pill } from './Shared';
import { formatIST } from '../lib/replay';
import { useReplay } from '../state/replay';

export function ReplayControls() {
  const { manifest, at, playing, setAt, step, setPlaying } = useReplay();
  const steps = manifest?.valid_at || [];
  const index = steps.indexOf(at);
  const heroDate = useMemo(() => manifest?.default_at ? formatIST(manifest.default_at, { weekday: 'short', year: 'numeric' }) : 'Scenario time', [manifest?.default_at]);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      const state = useReplay.getState();
      if (!state.manifest) return;
      const i = state.manifest.valid_at.indexOf(state.at);
      if (i >= state.manifest.valid_at.length - 1) state.setPlaying(false);
      else state.step(1);
    }, 1600);
    return () => window.clearInterval(timer);
  }, [playing]);
  if (!manifest) return null;
  return <section className="replay-controls" aria-label="Historical replay timeline">
    <div className="replay-meta">
      <div className="replay-mark"><span className="replay-dot"/><Pill tone="violet">REPLAY</Pill><span>{heroDate}</span><span className="replay-not-live">Historical view · not a live alert</span></div>
      <time dateTime={at}>{formatIST(at, { weekday: 'short', year: 'numeric' })} <b>{formatIST(at, { hour: '2-digit', minute: '2-digit', hour12: false })}</b> IST</time>
    </div>
    <div className="replay-slider-row">
      <button className="icon-button" aria-label="Previous replay step" onClick={() => step(-1)} disabled={index <= 0}><Icon name="back"/></button>
      <label className="sr-only" htmlFor="replay-slider">Replay timestamp</label>
      <input id="replay-slider" className="timeline-slider" type="range" min="0" max={Math.max(0, steps.length - 1)} value={Math.max(0, index)} onChange={(event) => setAt(steps[Number(event.target.value)])} aria-valuetext={formatIST(at)} />
      <button className="icon-button" aria-label={playing ? 'Pause replay' : 'Play replay'} onClick={() => setPlaying(!playing)}><Icon name={playing ? 'pause' : 'play'}/></button>
      <button className="icon-button" aria-label="Next replay step" onClick={() => step(1)} disabled={index >= steps.length - 1}><Icon name="next"/></button>
    </div>
    <div className="timeline-labels" aria-hidden="true">
      {steps.map((time, i) => <button key={time} onClick={() => setAt(time)} className={i === index ? 'active' : ''} title={formatIST(time)}>{formatIST(time, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })}</button>)}
    </div>
  </section>;
}

