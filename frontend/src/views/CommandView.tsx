import { useMemo } from 'react';
import type { DispatchCard, ReplayStep } from '../shared/types';
import { MapPanel } from '../components/MapPanel';
import { GaugeChart } from '../components/GaugeChart';
import { DispatchPanel } from '../components/DispatchPanel';
import { Icon, Panel, Pill, SectionEyebrow } from '../components/Shared';
import { formatIST } from '../lib/replay';
import { numberIN } from '../lib/format';

export function CommandView({ step, selectedColony, onSelectColony, onApproved }: {
  step: ReplayStep; selectedColony: string; onSelectColony: (id: string) => void; onApproved: (card: DispatchCard) => void;
}) {
  const plans = [...step.plans].sort((a, b) => b.priority - a.priority);
  const selected = plans.find((plan) => plan.colony_id === selectedColony) || plans[0] || null;
  const shelter = step.shelters.find((item) => item.shelter_id === selected?.primary.shelter_id) || null;
  const threshold = step.thresholds.find((item) => item.colony_id === selected?.colony_id);
  const roadCounts = useMemo(() => (step.roads || []).reduce((counts, edge) => { counts[edge.status] += 1; return counts; }, { green: 0, amber: 0, red: 0 }), [step.roads]);
  const stepTrap = step.trapSummary?.steps.find((item) => item.valid_at === step.at);
  return <main className="page-shell command-page">
    <header className="page-title-row"><div><SectionEyebrow>OPERATIONS · YAMUNA CORRIDOR</SectionEyebrow><h1>Flood response command</h1><p className="page-subtitle">Translate the river signal into a street plan, one replay step at a time.</p></div><Pill tone={step.sourceMode === 'fixture' ? 'violet' : 'green'}>{step.sourceMode === 'fixture' ? 'FIXTURE REPLAY' : 'STATIC DATA'}</Pill></header>
    <div className="provenance-banner"><Icon name="shield" size={16}/><span>{step.sourceNote}</span><span className="provenance-link">Every layer shows its source state below.</span></div>
    <div className="command-layout">
      <aside className="plan-rail" aria-label="Colony evacuation plans">
        <Panel title="Priority plans" aside={<Pill tone="neutral">{plans.length} plans</Pill>}>
          {plans.length ? <div className="plan-list" role="list">
            {plans.map((plan, index) => <button key={plan.colony_id} role="listitem" className={`plan-row ${selected?.colony_id === plan.colony_id ? 'plan-row-selected' : ''}`} onClick={() => onSelectColony(plan.colony_id)} aria-pressed={selected?.colony_id === plan.colony_id}>
              <span className={`plan-rank plan-rank-${index + 1}`}>{String(index + 1).padStart(2, '0')}</span><span className="plan-row-main"><strong>{plan.colony_id}</strong><small>Priority {Math.round(plan.priority * 100)}% · {numberIN(plan.ext?.assigned_people)} people</small></span>
              <span className={`plan-lead ${plan.lead_time_h <= 2 ? 'plan-lead-urgent' : ''}`}>{numberIN(plan.lead_time_h, 1)} h</span>
            </button>)}
          </div> : <div className="list-empty">No route plan exists for this timestamp.</div>}
          {step.unreachable.length > 0 && <div className="unreachable-block"><div className="unreachable-title"><Icon name="report" size={15}/>Boat / NDRF needed <Pill tone="red">{step.unreachable.length}</Pill></div>{step.unreachable.map((item) => <div key={item.colony_id} className="unreachable-row"><span>{item.colony_id}</span><small>{item.reason.replaceAll('_', ' ')}{item.population ? ` · ${numberIN(item.population)} people` : ''}</small></div>)}</div>}
        </Panel>
        <Panel title="Road watch" aside={step.roads ? <span className="small-source">{step.roads.length} edges</span> : <Pill>Unavailable</Pill>}>
          {step.roads ? <div className="road-status-list">
            {(['red', 'amber', 'green'] as const).map((status) => <div key={status} className={`road-status road-${status}`}><span className="road-symbol" aria-hidden="true">{status === 'red' ? '×' : status === 'amber' ? '!' : '✓'}</span><span>{status}</span><b>{roadCounts[status]}</b></div>)}
            <p className="road-note">Fixture provides edge IDs and status only; names and map geometry are unavailable at this step.</p>
          </div> : <p className="panel-note">No road status artifact is available for this replay step. No previous status is carried forward.</p>}
        </Panel>
        {step.trapSummary && <Panel title="Flood-blind counterfactual" aside={<Pill tone="violet">{step.sourceMode === 'fixture' ? 'SYNTHETIC' : 'SCENARIO'}</Pill>}>
          <div className="trap-counter"><strong>{numberIN(stepTrap?.trapped_population)}</strong><span>people the flood-blind plan would have trapped at this step</span></div>
          <p className="panel-note">{stepTrap?.roads.length ? `Roads in the counterfactual: ${stepTrap.roads.join(', ')}.` : 'No trapped population is reported for this step.'} This is a computed counterfactual, not an observed count.</p>
        </Panel>}
      </aside>
      <div className="command-main">
        <Panel className="map-panel-card">
          <MapPanel step={step} plan={selected} shelter={shelter}/>
          {selected && <div className="selected-plan-strip"><div><span className="eyebrow">SELECTED PLAN</span><strong>{selected.colony_id}</strong></div><div><span className="eyebrow">LEAD TIME</span><strong>{numberIN(selected.lead_time_h, 1)} h</strong></div><div><span className="eyebrow">PRIMARY SHELTER</span><strong>{shelter?.name_en || selected.primary.shelter_id}</strong></div><div><span className="eyebrow">FREE PLACES</span><strong>{numberIN(shelter?.free_beds)}</strong></div></div>}
        </Panel>
        <Panel className="chart-panel" title="Gauge & forecast" aside={<span className="chart-station">DELHI RAILWAY BRIDGE <span>· m above MSL</span></span>}>
          <GaugeChart gauges={step.gauges} forecasts={step.forecasts} at={step.at} thresholds={step.manifest.thresholds} manifest={step.manifest} streetLevel={threshold?.wet_at_level_m}/>
        </Panel>
        {selected && <div className="plan-detail-grid">
          <Panel title="Route details" aside={<Pill tone={selected.primary.max_depth_m <= 0.30 ? 'green' : 'red'}>{selected.primary.max_depth_m <= 0.30 ? '≤ 0.30 m reported' : 'Above 0.30 m'}</Pill>}>
            <div className="route-facts"><div><span>Primary</span><b>{selected.primary.shelter_id}</b><small>{numberIN(selected.primary.distance_m)} m · {numberIN(selected.primary.walk_min)} min</small></div><div><span>Backup</span><b>{selected.backup?.shelter_id || 'Not provided'}</b><small>{selected.backup ? `${numberIN(selected.backup.distance_m)} m · ${numberIN(selected.backup.walk_min)} min` : 'No alternate route in plan'}</small></div></div>
            <div className="avoid-list"><span className="eyebrow">AVOID</span>{selected.avoid.length ? selected.avoid.map((item) => <div key={item.name_en}><strong>{item.name_en}</strong><small>Cutoff {formatIST(item.cutoff_at)} · {item.edge_ids?.length || '—'} edge IDs</small></div>) : <p>No named road closure in this plan.</p>}</div>
            {selected.ext?.replanned_due_to && <p className="replanned-note">Route re-planned due to {selected.ext.replanned_due_to}</p>}
          </Panel>
          <Panel title="Data provenance" aside={<Pill tone={step.sourceMode === 'fixture' ? 'violet' : 'blue'}>{step.sourceMode.toUpperCase()}</Pill>}>
            <div className="source-list">{Object.entries(step.sources).map(([layer, source]) => <div key={layer}><span>{layer.replaceAll('_', ' ')}</span><Pill tone={source === 'static' ? 'green' : source === 'fixture' ? 'violet' : 'neutral'}>{source}</Pill></div>)}</div>
            <p className="panel-note">Replay time: {formatIST(step.at)} · {step.manifest.mode === 'replay' ? 'historical replay' : 'live mode'} · no live alert is being issued.</p>
          </Panel>
        </div>}
        <Panel className="dispatch-wrap"><DispatchPanel at={step.at} plan={selected} sourceMode={step.sourceMode} onApproved={onApproved}/></Panel>
      </div>
    </div>
  </main>;
}

