import { del, get, keys, set } from 'idb-keyval';

export interface QueuedReport {
  id: string;
  payload: Record<string, unknown>;
  photo: Blob | null;
  queuedAt: string;
}

const PREFIX = 'jaltaranga-report-queue:';

export async function queueReport(report: QueuedReport): Promise<void> {
  await set(`${PREFIX}${report.id}`, report);
}

export async function getQueuedReports(): Promise<QueuedReport[]> {
  const all = await keys();
  const selected = all.filter((key) => typeof key === 'string' && key.startsWith(PREFIX));
  return Promise.all(selected.map((key) => get<QueuedReport>(key as string))).then((items) => items.filter((item): item is QueuedReport => Boolean(item)));
}

export async function removeQueuedReport(id: string): Promise<void> {
  await del(`${PREFIX}${id}`);
}
