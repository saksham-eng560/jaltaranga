import { useEffect, useState } from 'react';
import type { DispatchCard, EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import type { Language } from '../lib/i18n';
import { translate } from '../lib/i18n';
import { getColonyPack, packIsStale, saveColonyPack, fetchAudioBlob, type ColonyPack } from '../lib/colonyPack';
import { loadDispatchCache } from '../data/client';
import { ColonyPlan } from '../components/ColonyPlan';
import { Icon, Pill } from '../components/Shared';

export function ColonyView({ step, colonyId, language, setLanguage, lite, setLite, currentDispatch, approvedDispatch, offlineOnly, offlinePack, onPackLoaded }: {
  step: ReplayStep | null; colonyId: string; language: Language; setLanguage: (value: Language) => void; lite: boolean; setLite: (value: boolean) => void;
  currentDispatch: DispatchCard | null; approvedDispatch: DispatchCard | null; offlineOnly: boolean; offlinePack: ColonyPack | null;
  onPackLoaded: (pack: ColonyPack | null) => void;
}) {
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle');
  const [localPack, setLocalPack] = useState<ColonyPack | null>(offlinePack);
  const [cachedDispatch, setCachedDispatch] = useState<DispatchCard | null>(null);
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key);
  useEffect(() => { setLocalPack(offlinePack); }, [offlinePack]);
  useEffect(() => {
    if (localPack || offlineOnly) return;
    void getColonyPack(colonyId).then((pack) => { if (pack) { setLocalPack(pack); onPackLoaded(pack); } }).catch(() => undefined);
  }, [colonyId, localPack, offlineOnly, onPackLoaded]);
  const plan: EvacuationPlan | null = offlineOnly && localPack ? localPack.plan : step?.plans.find((item) => item.colony_id === colonyId) || null;
  const source = offlineOnly && localPack ? { ...step, sourceMode: localPack.source } as ReplayStep : step;
  const shelter: Shelter | null = offlineOnly && localPack ? localPack.shelter : step?.shelters.find((item) => item.shelter_id === plan?.primary.shelter_id) || null;
  useEffect(() => {
    if (!step || offlineOnly || !plan) return;
    void loadDispatchCache(step.at, colonyId).then((card) => setCachedDispatch(card)).catch(() => setCachedDispatch(null));
  }, [step?.at, colonyId, offlineOnly, plan?.computed_at]);
  const approvedForPlan = approvedDispatch && approvedDispatch.plan_ref.computed_at === plan?.computed_at && approvedDispatch.plan_ref.colony_id === colonyId ? approvedDispatch : null;
  const dispatch = approvedForPlan || currentDispatch || (offlineOnly ? localPack?.dispatch || null : cachedDispatch);
  const isStale = localPack ? packIsStale(localPack.savedAt) : false;

  useEffect(() => {
    if (approvedDispatch && plan && shelter) void savePack(approvedDispatch);
  // Saving after approval is intentionally one-way and follows the API-confirmed response.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [approvedDispatch?.dispatch_id]);

  async function savePack(candidate?: DispatchCard | null) {
    if (!plan || !step) { setSaveState('failed'); return; }
    setSaveState('saving');
    try {
      let card = candidate || dispatch;
      if (!card) card = await loadDispatchCache(step.at, colonyId);
      if (card && !card.validation.passed) card = null;
      const audioBlob = await fetchAudioBlob(card);
      const pack: ColonyPack = {
        colonyId, scenarioId: step.manifest.scenario_id, at: step.at, savedAt: new Date().toISOString(),
        plan, shelter, dispatch: card, audioBlob, source: step.sourceMode,
      };
      await saveColonyPack(pack);
      setLocalPack(pack); onPackLoaded(pack); setSaveState('saved');
    } catch { setSaveState('failed'); }
  }

  const canSave = Boolean(plan && step && (dispatch?.validation.passed || localPack?.dispatch?.validation.passed));
  if (!step && !offlinePack) return <main className="resident-page"><div className="resident-loading">Loading saved colony plan…</div></main>;
  if (offlineOnly && !localPack) return <main className="resident-page"><div className="resident-offline-empty"><Pill tone="red">OFFLINE</Pill><h1>No saved plan on this device</h1><p>Open this colony while online and save its route before relying on offline access.</p><a className="button button-secondary" href="/command">Return to command</a></div></main>;

  return <main className="resident-page">
    <section className="resident-topline"><div><div className="resident-overline"><span className="resident-logo-mark"><img src="/logo.svg" alt="" /></span> JALTARANGA <span>·</span> YAMUNA CORRIDOR</div><Pill tone={offlineOnly ? 'amber' : 'violet'}>{offlineOnly ? 'OFFLINE PACK' : 'HISTORICAL REPLAY · NOT A LIVE ALERT'}</Pill></div>
      <div className="resident-controls"><button className="language-switch" onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')} aria-label="Switch resident language">{language === 'hi' ? 'EN' : 'हिंदी'}</button><button className={`lite-switch ${lite ? 'is-on' : ''}`} onClick={() => setLite(!lite)} aria-pressed={lite}>Lite {lite ? 'on' : 'off'}</button></div>
    </section>
    {isStale && <div className="stale-banner" role="status"><Icon name="report"/><span>Saved plan is over two hours old. Confirm current conditions before acting.</span></div>}
    <div className="resident-title"><div><span className="eyebrow">COLONY PLAN · {colonyId}</span><h1>{language === 'hi' ? 'आपके परिवार के लिए रास्ता' : 'A clear way to safety'}</h1></div><span className="resident-time">{offlineOnly ? 'Saved step' : 'Replay time'}<b>{step ? new Intl.DateTimeFormat(language === 'hi' ? 'hi-IN' : 'en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short', hour12: false }).format(new Date(step.at)) : localPack?.at}</b></span></div>
    {source && plan ? <ColonyPlan step={source} plan={plan} shelter={shelter} language={language} packTimestamp={offlineOnly ? localPack?.savedAt : undefined}/> : <div className="resident-offline-empty"><h2>{language === 'hi' ? 'इस समय के लिए रास्ता उपलब्ध नहीं है' : 'No route plan for this replay time'}</h2><p>{language === 'hi' ? 'कोई रास्ता अनुमान से नहीं बनाया गया है।' : 'No route has been inferred for a missing plan.'}</p><a href="/command">Choose a replay step with a plan</a></div>}
    {plan && <section className="resident-actions">
      {dispatch?.validation.passed && <div className="resident-dispatch"><div><Pill tone={dispatch.status === 'sent' ? 'green' : 'blue'}>{dispatch.status.toUpperCase()}</Pill><strong>{language === 'hi' ? 'सत्यापित निर्देश' : 'Validated dispatch'}</strong></div><p lang="hi">{dispatch.message_hi}</p>{dispatch.validation.fallback_used && <small>Validated template used · fallback reported by the API</small>}</div>}
      {dispatch && !dispatch.validation.passed && <div className="validation-blocked" role="alert"><strong>Instruction withheld</strong><span>Dispatch validation failed; its text is not shown or spoken.</span></div>}
      <div className="resident-action-buttons">
        <button className="button button-primary resident-save" disabled={!canSave || saveState === 'saving' || offlineOnly} onClick={() => void savePack()}><Icon name={saveState === 'saved' ? 'check' : 'download'}/>{saveState === 'saving' ? 'Saving…' : saveState === 'saved' ? t('saved') : t('saveOffline')}</button>
        {dispatch?.validation.passed && <ListenButton card={dispatch} blob={offlineOnly ? localPack?.audioBlob || null : null} language={language}/>}
      </div>
      {saveState === 'failed' && <p className="form-note error-note" role="alert">Could not save the offline pack. Check storage availability and try again.</p>}
      {saveState === 'saved' && localPack && <p className="save-confirmation" role="status"><Icon name="check" size={15}/>{t('saved')} · {new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(localPack.savedAt))}{isStale && <b> · outdated</b>}</p>}
      {!canSave && <p className="panel-note">Save becomes available when a validated dispatch accompanies this plan.</p>}
    </section>}
    <footer className="resident-footer-note"><span>Emergency help</span><a href="tel:1077">1077</a><a href="tel:112">112</a><small>Always verify with local authorities. This screen is a historical replay.</small></footer>
  </main>;
}

function ListenButton({ card, blob, language }: { card: DispatchCard; blob: Blob | null; language: Language }) {
  const [state, setState] = useState('');
  const play = async () => {
    if (!card.validation.passed) { setState('Validation failed; audio is blocked.'); return; }
    try {
      const source = blob ? URL.createObjectURL(blob) : card.audio_url_hi;
      if (source) {
        const audio = new Audio(source);
        await audio.play(); setState(blob ? 'Playing saved audio.' : 'Playing Hindi audio.');
        audio.onended = () => { if (blob) URL.revokeObjectURL(source); setState(''); };
        return;
      }
    } catch { /* Use the labelled device-voice fallback if remote or saved audio cannot play. */ }
    if (!('speechSynthesis' in window)) { setState('Audio is unavailable on this device.'); return; }
    const utterance = new SpeechSynthesisUtterance(card.message_hi);
    utterance.lang = 'hi-IN';
    utterance.onstart = () => setState('Device voice playing; it may need internet on desktop.');
    utterance.onerror = () => setState('Device voice could not start.');
    window.speechSynthesis.speak(utterance);
  };
  return <div className="listen-control"><button className="button button-secondary" onClick={() => void play()}><Icon name="audio"/>{translate(language, 'listen')}</button><small>{blob ? 'Saved audio' : card.audio_url_hi ? 'Polly audio · Hindi' : translate(language, 'deviceVoice')}</small>{state && <span role="status">{state}</span>}</div>;
}
