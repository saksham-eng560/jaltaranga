import type { ReplayStep } from '../shared/types';
import type { Language } from '../lib/i18n';
import { GaugeChart } from '../components/GaugeChart';
import { ColonyPlan } from '../components/ColonyPlan';
import { Icon, Panel, Pill, SectionEyebrow } from '../components/Shared';
import { numberIN } from '../lib/format';

export function CompareView({ step, colonyId, language }: { step: ReplayStep; colonyId: string; language: Language }) {
  const plan = step.plans.find((item) => item.colony_id === colonyId) || null;
  const shelter = step.shelters.find((item) => item.shelter_id === plan?.primary.shelter_id) || null;
  const last = [...step.gauges].reverse().find((row) => row.level_m !== null);
  const streetLevel = step.thresholds.find((item) => item.colony_id === colonyId)?.wet_at_level_m;
  return <main className="page-shell compare-page">
    <header className="page-title-row"><div><SectionEyebrow>ONE CLOCK · TWO KINDS OF WARNING</SectionEyebrow><h1>From basin warning to street plan</h1><p className="page-subtitle">A gauge describes the river. A colony plan describes the next action for a specific route.</p></div><Pill tone="violet">SYNCHRONIZED REPLAY</Pill></header>
    <div className="compare-grid">
      <Panel className="basin-pane" title="Basin warning" aside={<Pill tone="blue">CWC GAUGE</Pill>}>
        <div className="basin-gauge"><span>DELHI RAILWAY BRIDGE</span><strong>{last?.level_m === null || !last ? '—' : numberIN(last.level_m, 2)}<small>m</small></strong><div><span>{last?.source_ref || last?.source || 'No gauge anchor'}</span><span>{last?.qc_flag || 'unavailable'}</span></div></div>
        <GaugeChart gauges={step.gauges} forecasts={step.forecasts} at={step.at} thresholds={step.manifest.thresholds} manifest={step.manifest} streetLevel={streetLevel}/>
        <div className="basin-limitation"><Icon name="report"/><p>A basin level does not identify which lane floods, when a road becomes unsafe, or which shelter has space.</p></div>
        <small className="source-note">{step.sourceMode === 'fixture' ? 'Source-labeled anchor fixture. Routing outputs below are independently labeled synthetic.' : 'Source status and quality follow the scenario manifest.'}</small>
      </Panel>
      <Panel className="street-pane" title="Street plan" aside={<Pill tone={step.sourceMode === 'fixture' ? 'violet' : 'green'}>{step.sourceMode === 'fixture' ? 'SYNTHETIC FIXTURE' : 'SCENARIO DATA'}</Pill>}>
        {streetLevel !== undefined && <div className="compare-threshold"><span>Colony wet threshold</span><strong>{numberIN(streetLevel, 2)} m</strong><small>Gauge-equivalent · threshold artifact</small></div>}
        <ColonyPlan step={step} plan={plan} shelter={shelter} language={language} compact/>
        <div className="basin-limitation compare-addition"><Icon name="arrow"/><p>Jaltaranga adds a plan from route, shelter, and flood-risk artifacts; it does not replace the official gauge warning.</p></div>
      </Panel>
    </div>
  </main>;
}

