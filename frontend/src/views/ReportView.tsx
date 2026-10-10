import { useEffect, useState } from 'react';
import type { ReplayStep, ReportPostResponse } from '../shared/types';
import { compressReportImage } from '../lib/image';
import { getQueuedReports, queueReport, removeQueuedReport } from '../lib/reportQueue';
import { hasApiConfiguration, submitReport } from '../data/client';
import { Icon, Panel, Pill, SectionEyebrow } from '../components/Shared';
import { numberIN } from '../lib/format';

const BOUNDS = { minLon: 77.2, maxLon: 77.33, minLat: 28.53, maxLat: 28.75 };

export function ReportView({ step }: { step: ReplayStep }) {
  const [kind, setKind] = useState<'water_depth' | 'road_blocked' | 'shelter_full' | 'sos'>('water_depth');
  const [depth, setDepth] = useState('');
  const [longitude, setLongitude] = useState('77.2450');
  const [latitude, setLatitude] = useState('28.6550');
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [photoName, setPhotoName] = useState('');
  const [pending, setPending] = useState(0);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [receipt, setReceipt] = useState<ReportPostResponse['report'] | null>(null);

  const refreshQueue = async () => setPending((await getQueuedReports()).length);
  useEffect(() => { void refreshQueue(); }, []);
  useEffect(() => {
    if (!hasApiConfiguration()) return;
    const retry = () => { void flushQueue(); };
    window.addEventListener('online', retry);
    if (navigator.onLine) void flushQueue();
    return () => window.removeEventListener('online', retry);
    // Queue flushes only on an explicit browser reconnect; reports remain pending on failures.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function flushQueue() {
    if (!navigator.onLine || !hasApiConfiguration()) return;
    for (const queued of await getQueuedReports()) {
      try { await submitReport(queued.payload, queued.photo); await removeQueuedReport(queued.id); }
      catch { break; }
    }
    await refreshQueue();
  }

  async function choosePhoto(file?: File) {
    setPhoto(null); setPhotoName('');
    if (!file) return;
    try {
      const compressed = await compressReportImage(file);
      setPhoto(compressed); setPhotoName(`${file.name} · ${(compressed.size / 1024).toFixed(0)} KB JPEG`); setNote('Photo resized and converted to JPEG; embedded metadata is removed.');
    } catch (error) { setNote(error instanceof Error ? error.message : 'Could not prepare photo.'); }
  }

  const useLocation = () => {
    if (!('geolocation' in navigator)) { setNote('Location access is unavailable; enter coordinates manually.'); return; }
    setNote('Requesting one-time location…');
    navigator.geolocation.getCurrentPosition((position) => {
      setLongitude(position.coords.longitude.toFixed(5)); setLatitude(position.coords.latitude.toFixed(5)); setNote('Current location added. Review the coordinates before sending.');
    }, (error) => setNote(error.code === error.PERMISSION_DENIED ? 'Location permission was denied; enter coordinates manually.' : 'Could not read location; enter coordinates manually.'), { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 });
  };

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setNote(''); setReceipt(null);
    const lon = Number(longitude), lat = Number(latitude), depthCm = depth === '' ? null : Number(depth);
    if (!Number.isFinite(lon) || !Number.isFinite(lat) || lon < BOUNDS.minLon || lon > BOUNDS.maxLon || lat < BOUNDS.minLat || lat > BOUNDS.maxLat) {
      setNote('Enter a location inside the Yamuna pilot corridor.'); return;
    }
    if (kind === 'water_depth' && (!Number.isFinite(depthCm) || (depthCm as number) < 0 || (depthCm as number) > 1000)) { setNote('Enter a water depth from 0 to 1000 cm.'); return; }
    const id = crypto.randomUUID();
    let deviceId = localStorage.getItem('jt-anon-device');
    if (!deviceId) { deviceId = crypto.randomUUID(); localStorage.setItem('jt-anon-device', deviceId); }
    const payload = { kind, location: [lon, lat], depth_cm: kind === 'water_depth' ? depthCm : null, device_id: deviceId, replay_at: step.at };
    const queued = { id, payload, photo, queuedAt: new Date().toISOString() };
    setBusy(true);
    try {
      if (!navigator.onLine || !hasApiConfiguration()) {
        await queueReport(queued); await refreshQueue();
        setNote(!navigator.onLine ? 'Saved on this device. It will retry when online and the report API is configured.' : 'Report saved in the local queue; the API is not configured, so nothing was uploaded.');
        return;
      }
      const result = await submitReport(payload, photo);
      setReceipt(result.response.report);
      setNote(photo && result.response.upload && !result.photoUploaded ? 'The report was accepted, but the photo upload was not confirmed; the report remains without a confirmed photo.' : 'The report API confirmed receipt. It is unverified and is not yet published as a map pin.');
    } catch (error) {
      await queueReport(queued); await refreshQueue();
      setNote(`${error instanceof Error ? error.message : 'Report could not be submitted.'} Saved locally for retry; no upload was confirmed.`);
    } finally { setBusy(false); }
  }

  return <main className="page-shell report-page">
    <header className="page-title-row"><div><SectionEyebrow>COMMUNITY OBSERVATIONS · PILOT CORRIDOR</SectionEyebrow><h1>Report a local condition</h1><p className="page-subtitle">Send an unverified observation to the response team. Do not use this form for emergencies.</p></div><Pill tone={step.sourceMode === 'fixture' ? 'violet' : 'blue'}>{step.sourceMode === 'fixture' ? 'HISTORICAL REPLAY' : 'SCENARIO TIME'}</Pill></header>
    <div className="report-layout">
      <Panel className="report-form-panel">
        <form onSubmit={(event) => void onSubmit(event)}>
          <label className="field-label">What are you seeing?
            <select value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}>
              <option value="water_depth">Water on the street</option><option value="road_blocked">Road blocked</option><option value="shelter_full">Shelter full</option><option value="sos">Request help / SOS</option>
            </select>
          </label>
          {kind === 'water_depth' && <label className="field-label">Water depth <span className="field-unit">centimetres</span><input inputMode="decimal" type="number" min="0" max="1000" step="1" value={depth} onChange={(event) => setDepth(event.target.value)} required/></label>}
          <fieldset className="location-fields"><legend>Location <span className="field-unit">WGS84 coordinates</span></legend>
            <label className="field-label">Longitude<input type="number" step="0.00001" min={BOUNDS.minLon} max={BOUNDS.maxLon} value={longitude} onChange={(event) => setLongitude(event.target.value)} required/></label>
            <label className="field-label">Latitude<input type="number" step="0.00001" min={BOUNDS.minLat} max={BOUNDS.maxLat} value={latitude} onChange={(event) => setLatitude(event.target.value)} required/></label>
            <button type="button" className="text-button" onClick={useLocation}><Icon name="pin" size={16}/> Use this device's location</button>
          </fieldset>
          <label className="field-label">Photo <span className="field-unit">optional · JPEG, up to 1 MB</span>
            <input type="file" accept="image/*" capture="environment" onChange={(event) => void choosePhoto(event.currentTarget.files?.[0])}/>
          </label>
          {photoName && <p className="photo-ready"><Icon name="check" size={15}/>{photoName}</p>}
          <div className="report-replay"><span>Attached replay time</span><strong>{step.at}</strong><small>Report time and replay time are kept separate.</small></div>
          <button className="button button-primary report-submit" type="submit" disabled={busy}><Icon name="report"/>{busy ? 'Sending…' : 'Submit observation'}</button>
          {note && <p className="form-note" role="status">{note}</p>}
        </form>
      </Panel>
      <aside className="report-sidebar">
        <Panel title="Submission status" aside={pending > 0 && <Pill tone="amber">{pending} queued</Pill>}>
          {!hasApiConfiguration() && <div className="api-unavailable"><strong>Report API not configured</strong><p>Entries can be queued locally, but they will not be shown as uploaded or verified.</p></div>}
          {pending > 0 && <div className="queue-row"><span>Waiting for API confirmation</span><b>{pending}</b></div>}
          {receipt && <div className="report-receipt"><Pill tone="amber">UNVERIFIED</Pill><strong>Report accepted</strong><small>ID {receipt.report_id}</small><small>Trust score {numberIN(receipt.trust, 1)} · verification is not performed by this app.</small></div>}
          {!receipt && pending === 0 && hasApiConfiguration() && <p className="panel-note">No report has been submitted in this session.</p>}
        </Panel>
        <Panel title="Emergency help"><div className="emergency-contacts"><a href="tel:1077"><span>District disaster control</span><b>1077</b></a><a href="tel:112"><span>Emergency services</span><b>112</b></a></div><p className="panel-note">For immediate danger, call directly. Field reports are not monitored as an emergency hotline.</p></Panel>
        <Panel title="Privacy & limitations"><ul className="privacy-list"><li>Location is requested only when you press the location button.</li><li>Photos are resized and converted to JPEG to remove embedded metadata before upload.</li><li>Reports are unverified. This frontend does not apply a trust formula or fetch reports as map pins.</li></ul></Panel>
      </aside>
    </div>
  </main>;
}

