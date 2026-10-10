import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import type { Language } from '../lib/i18n';
import { translate } from '../lib/i18n';
import { formatCountdown, formatIST } from '../lib/replay';
import { numberIN } from '../lib/format';
import { Pill } from './Shared';
import { GeoRouteMap } from './GeoRouteMap';

export function ColonyPlan({ step, plan, shelter, language, compact = false, packTimestamp }: {
  step: ReplayStep; plan: EvacuationPlan | null; shelter: Shelter | null; language: Language; compact?: boolean; packTimestamp?: string;
}) {
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key);
  const countdown = plan ? formatCountdown(step.at, plan.t_submersion) : { kind: 'unknown' as const, text: t('noTime') };
  const threshold = step.thresholds.find((entry) => entry.colony_id === plan?.colony_id);
  if (!plan) {
    const unreachable = step.unreachable[0];
    return <div className="colony-state" role="status">
      <Pill tone={unreachable?.reason === 'already_wet' ? 'red' : 'amber'}>{unreachable?.reason === 'already_wet' ? 'SHELTER IN PLACE' : 'NO ROUTE PLAN'}</Pill>
      <h2>{unreachable?.reason === 'already_wet' ? 'पानी पहले ही पहुँच चुका है' : 'A route plan is not available for this time.'}</h2>
      <p>{unreachable?.reason === 'already_wet' ? 'पानी से होकर बाहर न निकलें। ऊपरी मंज़िल पर जाएँ और 1077 / 112 पर मदद के लिए कॉल करें।' : 'The selected step has no matching evacuation plan. No route has been inferred.'}</p>
      <div className="call-strip"><span>{t('call')}</span><a href="tel:1077">1077</a><a href="tel:112">112</a></div>
    </div>;
  }
  return <div className={`colony-plan ${compact ? 'colony-plan-compact' : ''}`} lang={language === 'hi' ? 'hi' : undefined}>
    <div className={`countdown-hero countdown-${countdown.kind}`}>
      <div className="countdown-heading"><span className="eyebrow">{t('waterTime')}</span><Pill tone={countdown.kind === 'future' ? 'amber' : countdown.kind === 'elapsed' ? 'red' : 'neutral'}>{countdown.kind === 'future' ? 'FORECAST PLAN' : countdown.kind === 'elapsed' ? 'TIME PASSED' : 'UNAVAILABLE'}</Pill></div>
      <strong>{countdown.kind === 'future' ? countdown.text : countdown.kind === 'elapsed' ? (language === 'hi' ? 'पानी का समय बीत चुका है' : 'Arrived') : '—'}</strong>
      <span className="countdown-caption">{countdown.kind === 'future' ? `${language === 'hi' ? 'योजना में पानी का समय' : 'Plan time'} · ${formatIST(plan.t_submersion)}` : countdown.text}</span>
      <div className="countdown-band">
        <div><span>{t('earliest')}</span><b>{plan.t_submersion_earliest ? formatCountdown(step.at, plan.t_submersion_earliest).text : 'Not provided'}</b></div>
        <div><span>{t('latest')}</span><b>{plan.t_submersion_latest ? formatCountdown(step.at, plan.t_submersion_latest).text : 'Not established'}</b></div>
      </div>
      <p className="precision-note">Times are shown from the plan builder; the interface does not recalculate the forecast band.</p>
    </div>
    {threshold && <div className="street-threshold"><span className="threshold-symbol">↗</span><div><span>Street-level threshold <small>· gauge-equivalent</small></span><strong>{numberIN(threshold.wet_at_level_m, 2)} m</strong></div><small>150 m colony buffer · {step.sources.thresholds === 'fixture' ? 'synthetic fixture' : 'scenario artifact'}</small></div>}
    <div className="resident-route-head"><div><span className="eyebrow">{t('route')}</span><h2>{plan.primary.via_names_hi?.[0] || plan.primary.via_names_en?.[0] || (language === 'hi' ? 'निर्धारित सुरक्षित मार्ग' : 'Planned safe route')}</h2></div><Pill tone={plan.primary.max_depth_m <= 0.3 ? 'green' : 'red'}>{plan.primary.max_depth_m <= 0.3 ? `${numberIN(plan.primary.max_depth_m, 2)} m reported max` : 'Route exceeds 0.30 m'}</Pill></div>
    <GeoRouteMap step={step} plan={plan} shelter={shelter} compact/>
    <div className="resident-shelter">
      <div className="shelter-icon">⌂</div><div className="resident-shelter-main"><span className="eyebrow">{t('shelter')}</span><strong>{language === 'hi' ? shelter?.name_hi || 'केंद्र उपलब्ध नहीं' : shelter?.name_en || 'Shelter unavailable'}</strong><small>{shelter?.shelter_id || plan.primary.shelter_id} · {numberIN(plan.primary.distance_m / 1000, 1)} km · {numberIN(plan.primary.walk_min)} min</small></div>
      <div className="free-beds"><b>{numberIN(shelter?.free_beds)}</b><span>{t('freeBeds')}</span></div>
    </div>
    <div className="resident-avoid">
      <span className="avoid-sign">!</span><div><strong>{t('avoid')}</strong>{plan.avoid.length ? <p>{plan.avoid.map((road) => language === 'hi' ? road.name_hi : road.name_en).join(', ')} <small>· from {formatIST(plan.avoid[0].cutoff_at)}</small></p> : <p>{language === 'hi' ? 'इस योजना में नामित बंद रास्ता नहीं है।' : 'No named closure is listed in this plan.'}</p>}</div>
    </div>
    <div className="resident-footer">
      {packTimestamp && <div className="saved-stamp">Saved {formatIST(packTimestamp)} · may be outdated</div>}
      <div className="call-strip"><span>{t('call')}</span><a href="tel:1077">1077</a><a href="tel:112">112</a></div>
    </div>
    {step.sourceMode === 'fixture' && <p className="resident-demo-note">{t('synthetic')} · this route and shelter allocation are examples, not operational instructions.</p>}
  </div>;
}

