import { useEffect, useState } from 'react';
import type { DispatchCard, EvacuationPlan } from '../shared/types';
import { approveDispatch, draftDispatch, hasApiConfiguration, listDispatches, loadDispatchCache } from '../data/client';
import { Icon, Pill } from './Shared';
import { formatIST } from '../lib/replay';

type CardOrigin = 'api' | 'cache' | 'fixture';

export function DispatchPanel({ at, plan, sourceMode, onApproved, compact = false }: {
  at: string; plan: EvacuationPlan | null; sourceMode: 'static' | 'fixture'; onApproved?: (card: DispatchCard) => void; compact?: boolean;
}) {
  const [card, setCard] = useState<DispatchCard | null>(null);
  const [origin, setOrigin] = useState<CardOrigin | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [inbox, setInbox] = useState<DispatchCard[]>([]);
  useEffect(() => {
    let active = true;
    setCard(null); setOrigin(null); setNote(''); setInbox([]);
    if (!plan) return () => { active = false; };
    void loadDispatchCache(at, plan.colony_id).then((cached) => {
      if (active && cached) { setCard(cached); setOrigin(sourceMode === 'fixture' ? 'fixture' : 'cache'); }
    }).catch(() => undefined);
    if (hasApiConfiguration()) void listDispatches().then((cards) => { if (active) setInbox(cards.slice(0, 3)); }).catch(() => undefined);
    return () => { active = false; };
  }, [at, plan, sourceMode]);

  const onDraft = async () => {
    if (!plan) return;
    setBusy(true); setNote('');
    try {
      const next = await draftDispatch(at, plan.colony_id);
      setCard(next); setOrigin('api');
      if (!next.validation.passed) setNote('The API returned a card that did not pass validation. Its text is withheld.');
    } catch (error) {
      try {
        const cached = await loadDispatchCache(at, plan.colony_id);
        if (cached) {
          setCard(cached); setOrigin(sourceMode === 'fixture' ? 'fixture' : 'cache');
          setNote(`API unavailable. Showing a ${sourceMode === 'fixture' ? 'fixture' : 'pre-drafted cached'} card; it cannot be sent from this screen.`);
        } else setNote(error instanceof Error ? error.message : 'Dispatch draft unavailable.');
      } catch { setNote(error instanceof Error ? error.message : 'Dispatch draft unavailable.'); }
    } finally { setBusy(false); }
  };

  const onApprove = async () => {
    if (!card || origin !== 'api' || !card.validation.passed) return;
    setBusy(true); setNote('');
    try {
      const sent = await approveDispatch(card.dispatch_id);
      setCard(sent); onApproved?.(sent);
      setNote(sent.status === 'sent' ? 'API confirmed this dispatch as sent.' : `API returned status: ${sent.status}.`);
      try { setInbox(await listDispatches()); } catch { /* An approval response remains the source of truth. */ }
    } catch (error) { setNote(error instanceof Error ? error.message : 'Approval could not be confirmed.'); }
    finally { setBusy(false); }
  };

  return <section className={`dispatch-panel ${compact ? 'dispatch-panel-compact' : ''}`} aria-labelledby="dispatch-heading">
    <div className="dispatch-heading-row"><div><div className="eyebrow">VERIFIED INSTRUCTIONS</div><h2 id="dispatch-heading">Dispatch</h2></div>
      {card && <Pill tone={card.validation.passed ? card.status === 'sent' ? 'green' : 'blue' : 'red'}>{card.validation.passed ? card.status.toUpperCase() : 'WITHHELD'}</Pill>}
    </div>
    {!plan ? <div className="dispatch-empty">Select a colony with a route plan to draft an instruction.</div> : <>
      <p className="dispatch-intro">Every place, time, road, and number comes from the selected plan and is checked by the dispatch validator.</p>
      {card && <div className="dispatch-card">
        <div className="dispatch-card-meta"><span><Icon name="shield" size={15}/> Validation {card.validation.passed ? 'passed' : 'failed'}</span><span>{origin === 'api' ? 'API response' : origin === 'cache' ? 'Pre-draft cache' : 'Synthetic fixture'}</span></div>
        {!card.validation.passed ? <div className="validation-blocked" role="alert"><strong>Instruction withheld</strong><span>Validation did not pass. Unverified text is not displayed or read aloud.</span></div> : <>
          {card.validation.fallback_used && <div className="fallback-banner"><strong>Template fallback used.</strong> {card.validation.fallback_fields?.length ? `Fallback fields: ${card.validation.fallback_fields.join(', ')}.` : 'Code supplied the validated message.'}</div>}
          {origin !== 'api' && <div className="fixture-callout">This example is synthetic and cannot be approved or sent.</div>}
          <div className="dispatch-language"><span>हिन्दी</span><p lang="hi">{card.message_hi}</p></div>
          <details className="dispatch-english"><summary>English version</summary><p>{card.message_en}</p></details>
          <div className="sms-preview"><div><span>SMS preview</span><b>{card.sms_hi.length}/160</b></div><p lang="hi">{card.sms_hi}</p></div>
          <div className="validation-checks" aria-label="Validation checks">
            {card.validation.checks.map((check) => <Pill key={check} tone={(card.validation.failed_checks || []).includes(check) ? 'red' : 'green'}><Icon name={(card.validation.failed_checks || []).includes(check) ? 'close' : 'check'} size={12}/>{check.replaceAll('_', ' ')}</Pill>)}
          </div>
          <div className="dispatch-footer"><span>Prepared {formatIST(card.ts)}</span>{card.audio_url_hi && <Pill tone="blue">Hindi audio available</Pill>}</div>
        </>}
      </div>}
      {note && <p className="form-note" role="status">{note}</p>}
      <div className="dispatch-actions">
        <button className="button button-secondary" onClick={() => void onDraft()} disabled={busy || !hasApiConfiguration()} title={!hasApiConfiguration() ? 'Configure VITE_API_BASE to draft through the API.' : undefined}>
          <Icon name="command" size={16}/>{busy ? 'Working…' : card ? 'Refresh draft' : 'Draft instruction'}
        </button>
        <button className="button button-primary" onClick={() => void onApprove()} disabled={busy || !card?.validation.passed || origin !== 'api' || card.status !== 'draft' || sourceMode === 'fixture'}>
          <Icon name="check" size={16}/>{busy ? 'Working…' : 'Approve & send'}
        </button>
      </div>
      {sourceMode === 'fixture' && card?.validation.passed && <p className="api-unavailable">Fixture-based routes cannot be approved or sent as operational instructions.</p>}
      {!hasApiConfiguration() && <p className="api-unavailable">Write API not configured. A matching pre-drafted card may be previewed, but cannot be sent.</p>}
      {inbox.length > 0 && <div className="dispatch-inbox"><h3>Recent dispatches</h3>{inbox.map((item) => <div key={item.dispatch_id}><span>{item.alert_type.replaceAll('_', ' ')}</span><Pill tone={item.status === 'sent' ? 'green' : 'neutral'}>{item.status}</Pill></div>)}</div>}
    </>}
  </section>;
}

