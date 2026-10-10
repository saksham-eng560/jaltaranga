import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import type { DispatchCard, Manifest, ReplayStep } from './shared/types';
import { loadManifest, loadReplayStep } from './data/client';
import { useReplay } from './state/replay';
import { ReplayControls } from './components/ReplayControls';
import { Icon, Pill } from './components/Shared';
import { getColonyPack, fetchAudioBlob, saveColonyPack, type ColonyPack } from './lib/colonyPack';
import type { Language } from './lib/i18n';
import { formatIST } from './lib/replay';

const CommandView = lazy(() => import('./views/CommandView').then((module) => ({ default: module.CommandView })));
const ColonyView = lazy(() => import('./views/ColonyView').then((module) => ({ default: module.ColonyView })));
const CompareView = lazy(() => import('./views/CompareView').then((module) => ({ default: module.CompareView })));
const ReportView = lazy(() => import('./views/ReportView').then((module) => ({ default: module.ReportView })));

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false, staleTime: 20_000 } } });
const scenarioId = import.meta.env.VITE_SCENARIO_ID || 'yamuna-2023-07';
const heroColony = import.meta.env.VITE_HERO_COLONY || 'DEL-YP-04';

function pathView(pathname: string): 'command' | 'colony' | 'compare' | 'report' {
  if (pathname.startsWith('/colony')) return 'colony';
  if (pathname.startsWith('/compare')) return 'compare';
  if (pathname.startsWith('/report')) return 'report';
  return 'command';
}

function parseColony(pathname: string, search: string): string {
  const pathId = pathname.startsWith('/colony/') ? decodeURIComponent(pathname.slice('/colony/'.length).split('/')[0]) : '';
  return new URLSearchParams(search).get('colony') || pathId || heroColony;
}

function AppBody() {
  const manifest = useReplay((state) => state.manifest);
  const at = useReplay((state) => state.at);
  const setManifest = useReplay((state) => state.setManifest);
  const setAt = useReplay((state) => state.setAt);
  const [view, setView] = useState(() => pathView(window.location.pathname));
  const [colonyId, setColonyId] = useState(() => parseColony(window.location.pathname, window.location.search));
  const [language, setLanguage] = useState<Language>(() => (localStorage.getItem('jt-language') as Language) || (pathView(window.location.pathname) === 'colony' ? 'hi' : 'en'));
  const [highContrast, setHighContrast] = useState(() => localStorage.getItem('jt-high-contrast') === 'true');
  const [lite, setLite] = useState(() => new URLSearchParams(window.location.search).get('lite') === '1');
  const [demo, setDemo] = useState(() => new URLSearchParams(window.location.search).get('demo') === '1');
  const [offlinePack, setOfflinePack] = useState<ColonyPack | null>(null);
  const [offlineOnly, setOfflineOnly] = useState(false);
  const [approvedDispatch, setApprovedDispatch] = useState<DispatchCard | null>(null);
  const [bootstrapError, setBootstrapError] = useState('');
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    let active = true;
    void (async () => {
      const currentView = pathView(window.location.pathname);
      const currentColony = parseColony(window.location.pathname, window.location.search);
      if (!navigator.onLine && currentView === 'colony') {
        const pack = await getColonyPack(currentColony).catch(() => undefined);
        if (pack && active) {
          const savedSource = pack.source === 'static' ? 'real' : 'fixture';
          const offlineManifest: Manifest = { scenario_id: pack.scenarioId, mode: 'replay', start: pack.at, end: pack.at, valid_at: [pack.at], default_at: pack.at, artefacts: { plans: savedSource, shelters: savedSource } };
          setOfflinePack(pack); setOfflineOnly(true); setManifest(offlineManifest); setAt(pack.at, false);
          return;
        }
      }
      const loaded = await loadManifest();
      if (active) setManifest(loaded);
    })().catch((error: unknown) => { if (active) setBootstrapError(error instanceof Error ? error.message : 'Replay data is unavailable.'); });
    const onPop = () => {
      const nextView = pathView(window.location.pathname);
      setView(nextView); setColonyId(parseColony(window.location.pathname, window.location.search));
      setDemo(new URLSearchParams(window.location.search).get('demo') === '1');
      setLite(new URLSearchParams(window.location.search).get('lite') === '1');
      const requested = new URLSearchParams(window.location.search).get('at');
      if (requested && useReplay.getState().manifest) useReplay.getState().setAt(requested, false);
    };
    const goOnline = () => { setOnline(true); setOfflineOnly(false); void loadManifest().then(setManifest).catch(() => undefined); };
    const goOffline = () => setOnline(false);
    window.addEventListener('popstate', onPop); window.addEventListener('online', goOnline); window.addEventListener('offline', goOffline);
    return () => { active = false; window.removeEventListener('popstate', onPop); window.removeEventListener('online', goOnline); window.removeEventListener('offline', goOffline); };
  }, [setAt, setManifest]);

  useEffect(() => { document.documentElement.classList.toggle('high-contrast', highContrast); localStorage.setItem('jt-high-contrast', String(highContrast)); }, [highContrast]);
  useEffect(() => { localStorage.setItem('jt-language', language); }, [language]);
  useEffect(() => {
    if (online || view !== 'colony') return;
    if (offlinePack) { setOfflineOnly(true); return; }
    void getColonyPack(colonyId).then((pack) => { if (pack) { setOfflinePack(pack); setOfflineOnly(true); } }).catch(() => undefined);
  }, [online, view, colonyId, offlinePack]);

  const stepQuery = useQuery({
    queryKey: ['replay-step', scenarioId, at], queryFn: () => loadReplayStep(at),
    enabled: Boolean(manifest && at && !offlineOnly),
  });
  const step = stepQuery.data || null;
  const selectedPlan = step?.plans.find((plan) => plan.colony_id === colonyId) || null;
  const selectedShelter = step?.shelters.find((shelter) => shelter.shelter_id === selectedPlan?.primary.shelter_id) || null;

  const navigate = useCallback((target: 'command' | 'colony' | 'compare' | 'report', nextColony = colonyId) => {
    const url = new URL(window.location.href);
    const nextPath = target === 'command' ? '/command' : target === 'colony' ? `/colony/${encodeURIComponent(nextColony)}` : `/${target}`;
    url.pathname = nextPath;
    if (at) url.searchParams.set('at', at);
    if (target === 'compare') url.searchParams.set('colony', nextColony);
    else url.searchParams.delete('colony');
    window.history.pushState({}, '', url); setView(target); setColonyId(nextColony);
    if (target !== 'colony') setOfflineOnly(false);
    if (target === 'colony' && !localStorage.getItem('jt-language')) setLanguage('hi');
  }, [at, colonyId]);

  const chooseColony = useCallback((id: string) => {
    setColonyId(id);
    const url = new URL(window.location.href); url.searchParams.set('colony', id); window.history.replaceState({}, '', url);
  }, []);

  const setLanguagePref = useCallback((value: Language) => { setLanguage(value); localStorage.setItem('jt-language', value); }, []);
  const onApproved = useCallback((card: DispatchCard) => {
    setApprovedDispatch(card);
    if (!step || !selectedPlan) return;
    void (async () => {
      const audioBlob = await fetchAudioBlob(card);
      const pack: ColonyPack = { colonyId: selectedPlan.colony_id, scenarioId: step.manifest.scenario_id, at: step.at, savedAt: new Date().toISOString(), plan: selectedPlan, shelter: selectedShelter, dispatch: card, audioBlob, source: step.sourceMode };
      await saveColonyPack(pack).catch(() => undefined);
      setOfflinePack(pack);
    })();
  }, [step, selectedPlan, selectedShelter]);

  useEffect(() => {
    if (!demo) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
      if (event.code === 'Space') { event.preventDefault(); useReplay.getState().setPlaying(!useReplay.getState().playing); }
      else if (event.key === 'ArrowLeft') { event.preventDefault(); useReplay.getState().step(-1); }
      else if (event.key === 'ArrowRight') { event.preventDefault(); useReplay.getState().step(1); }
      else if (['1', '2', '3', '4'].includes(event.key)) navigate((['command', 'colony', 'compare', 'report'] as const)[Number(event.key) - 1]);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [demo, navigate]);

  const routes = useMemo(() => [
    { key: 'command' as const, label: 'Command', icon: 'command' },
    { key: 'colony' as const, label: 'Colony', icon: 'home' },
    { key: 'compare' as const, label: 'Compare', icon: 'compare' },
    { key: 'report' as const, label: 'Report', icon: 'report' },
  ], []);

  const offlineStep: ReplayStep | null = offlinePack && manifest ? {
    manifest, at: offlinePack.at, gauges: [], forecasts: [], flood: null, roads: null, roadGeometry: null,
    plans: [offlinePack.plan], shelters: offlinePack.shelter ? [offlinePack.shelter] : [], colonies: null, unreachable: [], thresholds: [], trapSummary: null,
    sources: { plans: offlinePack.source, shelters: offlinePack.source, roads: 'missing', flood: 'missing', gauges: 'missing', colonies: 'missing', thresholds: 'missing', unreachable: 'missing' },
    sourceMode: offlinePack.source, sourceNote: 'Loaded from this device’s saved Colony Pack.',
  } : null;
  const activeStep = offlineOnly ? offlineStep : step;

  if (bootstrapError) return <main className="startup-error"><Icon name="report" size={24}/><h1>Replay unavailable</h1><p>{bootstrapError}</p><button className="button button-secondary" onClick={() => window.location.reload()}>Retry</button></main>;
  if (!manifest) return <main className="startup-loading"><span className="loading-pulse"/><strong>Preparing the replay</strong><small>Reading the manifest and local fixture pack…</small></main>;

  return <div className={`app-root ${demo ? 'director-mode' : ''} ${view === 'colony' ? 'resident-app' : ''}`}>
    {!demo && <header className="app-header">
      <a className="brand-lockup" href="/command" onClick={(e) => { e.preventDefault(); navigate('command'); }}><span className="brand-mark">J</span><span><strong>jaltaranga</strong><small>Predict · Route · Protect</small></span></a>
      <div className="header-clock"><span>{formatIST(at, { month: 'long', day: 'numeric', year: 'numeric', hour: undefined, minute: undefined })}</span><i/><b>{formatIST(at, { hour: '2-digit', minute: '2-digit', hour12: false, day: undefined, month: undefined, year: undefined })}</b> IST</div>
      <nav className="primary-nav" aria-label="Main navigation">{routes.map((route) => <a key={route.key} href={route.key === 'colony' ? `/colony/${colonyId}` : `/${route.key}`} onClick={(e) => { e.preventDefault(); navigate(route.key); }} className={view === route.key ? 'nav-active' : ''} aria-current={view === route.key ? 'page' : undefined}><Icon name={route.icon}/><span>{route.label}</span></a>)}</nav>
      <div className="header-tools"><span className={`network-indicator ${online ? 'network-online' : 'network-offline'}`}><i/>System status: {online ? 'Active' : 'Offline'}</span>
        <button className="header-tool-button" onClick={() => setLanguagePref(language === 'hi' ? 'en' : 'hi')} aria-label="Switch language">{language === 'hi' ? 'EN' : 'हि'}</button>
        <button className={`header-tool-button contrast-toggle ${highContrast ? 'enabled' : ''}`} onClick={() => setHighContrast(!highContrast)} aria-pressed={highContrast} aria-label="Toggle high contrast">◐<span className="sr-only">High contrast</span></button>
      </div>
    </header>}
    {demo && <div className="director-strip"><span><b>DIRECTOR MODE</b> · {view.toUpperCase()} · {at}</span><small>Space play/pause · ← → replay steps · 1–4 views</small><button onClick={() => setDemo(false)} className="director-exit">Exit</button></div>}
    {view !== 'command' && !offlineOnly && <ReplayControls/>}
    {!demo && !offlineOnly && view !== 'command' && <div className="replay-ribbon"><Icon name="shield" size={14}/> Historical flood replay · not a live alert<Pill tone={step?.sourceMode === 'fixture' ? 'violet' : 'blue'}>{step?.sourceMode === 'fixture' ? 'Synthetic route examples' : 'Scenario artifacts'}</Pill></div>}
    {stepQuery.isFetching && !stepQuery.data && <div className="step-loading" role="status">Loading artifacts for {at}…</div>}
    {stepQuery.isError && !offlineOnly && <div className="step-error" role="alert"><strong>Selected replay step could not be loaded.</strong><span>{stepQuery.error instanceof Error ? stepQuery.error.message : 'Data source unavailable.'} No layers from another step are shown.</span><button onClick={() => void stepQuery.refetch()}>Retry</button></div>}
    {activeStep && !stepQuery.isError && <Suspense fallback={<div className="step-loading" role="status">Opening {view} view…</div>}>
      {view === 'command' && <CommandView step={activeStep} selectedColony={colonyId} onSelectColony={chooseColony} onApproved={onApproved}/>}
      {view === 'colony' && <ColonyView step={activeStep} colonyId={colonyId} language={language} setLanguage={setLanguagePref} lite={lite} setLite={setLite} currentDispatch={null} approvedDispatch={approvedDispatch} offlineOnly={offlineOnly} offlinePack={offlinePack} onPackLoaded={setOfflinePack}/>}
      {view === 'compare' && <CompareView step={activeStep} colonyId={colonyId} language={language}/>}
      {view === 'report' && <ReportView step={activeStep}/>}
    </Suspense>}
    {!activeStep && !stepQuery.isFetching && !stepQuery.isError && <div className="step-error"><strong>Replay data unavailable for this timestamp.</strong><span>Check the scenario manifest and static artifact configuration.</span></div>}
    {!demo && <footer className="app-footer"><span>Jaltaranga · Historical replay</span><span>Every displayed value retains its source label.</span><a href="/report" onClick={(e) => { e.preventDefault(); navigate('report'); }}>Report a condition <Icon name="arrow" size={13}/></a></footer>}
  </div>;
}

export default function App() { return <QueryClientProvider client={queryClient}><AppBody/></QueryClientProvider>; }
