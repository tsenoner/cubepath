/**
 * Local persistence: progress, spaced-repetition cards, review log, settings.
 * IndexedDB via `idb`; everything works offline; JSON export/import as the
 * belt-and-braces backup (see research brief §5).
 */
import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { Card } from "ts-fsrs";

export type CaseStatus = "unseen" | "learning" | "learned";

export interface ProgressEntry {
  caseId: string;
  status: CaseStatus;
  updatedAt: number;
}

export interface ReviewLogEntry {
  caseId: string;
  rating: number;
  review: Date;
}

interface CubepathDB extends DBSchema {
  progress: { key: string; value: ProgressEntry };
  cards: {
    key: string;
    value: Card & { caseId: string };
    indexes: { "by-due": Date };
  };
  reviews: { key: number; value: ReviewLogEntry; indexes: { "by-case": string } };
  settings: { key: string; value: unknown };
}

const DB_NAME = "cubepath";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<CubepathDB>> | null = null;

/** Test hook: drop the cached connection (e.g. after swapping IndexedDB). */
export function _resetDBCache(): void {
  dbPromise = null;
}

export function getDB(): Promise<IDBPDatabase<CubepathDB>> {
  dbPromise ??= openDB<CubepathDB>(DB_NAME, DB_VERSION, {
    upgrade(db, oldVersion) {
      if (oldVersion < 1) {
        db.createObjectStore("progress", { keyPath: "caseId" });
        const cards = db.createObjectStore("cards", { keyPath: "caseId" });
        cards.createIndex("by-due", "due");
        const reviews = db.createObjectStore("reviews", { autoIncrement: true });
        reviews.createIndex("by-case", "caseId");
        db.createObjectStore("settings");
      }
    },
    blocking() {
      // A newer tab wants to upgrade — release the connection.
      void getDB().then((db) => db.close());
      dbPromise = null;
    },
  });
  return dbPromise;
}

export async function getProgress(caseId: string): Promise<ProgressEntry | undefined> {
  return (await getDB()).get("progress", caseId);
}

export async function allProgress(): Promise<ProgressEntry[]> {
  return (await getDB()).getAll("progress");
}

export async function setStatus(caseId: string, status: CaseStatus): Promise<void> {
  await (await getDB()).put("progress", { caseId, status, updatedAt: Date.now() });
}

/** Persist a graded review atomically: card state + log entry + progress. */
export async function recordReview(
  card: Card & { caseId: string },
  rating: number,
  when: Date,
): Promise<void> {
  const db = await getDB();
  const tx = db.transaction(["cards", "reviews", "progress"], "readwrite");
  await Promise.all([
    tx.objectStore("cards").put(card),
    tx.objectStore("reviews").add({ caseId: card.caseId, rating, review: when }),
    tx.objectStore("progress").put({ caseId: card.caseId, status: "learning", updatedAt: Date.now() }),
    tx.done,
  ]);
}

export async function getCard(caseId: string): Promise<(Card & { caseId: string }) | undefined> {
  return (await getDB()).get("cards", caseId);
}

/** Cards due at or before `now`, soonest first. */
export async function dueCards(now: Date): Promise<(Card & { caseId: string })[]> {
  const db = await getDB();
  return db.getAllFromIndex("cards", "by-due", IDBKeyRange.upperBound(now));
}

/** Ask the browser to protect the data from eviction. Call on first save, in a user gesture. */
export async function ensurePersistence(): Promise<boolean> {
  if (typeof navigator === "undefined" || !navigator.storage?.persist) return false;
  if (await navigator.storage.persisted()) return true;
  return navigator.storage.persist();
}

// ── Backup ────────────────────────────────────────────────────────────

interface BackupEnvelope {
  app: "cubepath";
  schemaVersion: number;
  exportedAt: string;
  data: {
    progress: ProgressEntry[];
    cards: (Card & { caseId: string })[];
    reviews: ReviewLogEntry[];
    settings: { key: string; value: unknown }[];
  };
}

export async function exportBackup(): Promise<BackupEnvelope> {
  const db = await getDB();
  const [progress, cards, reviews, settingKeys] = await Promise.all([
    db.getAll("progress"),
    db.getAll("cards"),
    db.getAll("reviews"),
    db.getAllKeys("settings"),
  ]);
  const settings = await Promise.all(
    settingKeys.map(async (key) => ({ key, value: await db.get("settings", key) })),
  );
  return {
    app: "cubepath",
    schemaVersion: DB_VERSION,
    exportedAt: new Date().toISOString(),
    data: { progress, cards, reviews, settings },
  };
}

export async function importBackup(raw: unknown): Promise<void> {
  const env = raw as BackupEnvelope;
  if (env?.app !== "cubepath" || !env.data) throw new Error("Not a Cubepath backup file");
  if (env.schemaVersion > DB_VERSION) {
    throw new Error("Backup was made by a newer version of Cubepath");
  }
  const db = await getDB();
  const tx = db.transaction(["progress", "cards", "reviews", "settings"], "readwrite");
  await Promise.all([
    tx.objectStore("progress").clear(),
    tx.objectStore("cards").clear(),
    tx.objectStore("reviews").clear(),
    tx.objectStore("settings").clear(),
  ]);
  for (const p of env.data.progress ?? []) await tx.objectStore("progress").put(p);
  for (const c of env.data.cards ?? []) {
    // Revive dates: the by-due index needs real Date objects (ts-fsrs itself
    // tolerates ISO strings, which would silently break the due queue).
    await tx.objectStore("cards").put({
      ...c,
      due: new Date(c.due),
      last_review: c.last_review ? new Date(c.last_review) : undefined,
    });
  }
  for (const r of env.data.reviews ?? []) {
    await tx.objectStore("reviews").add({ ...r, review: new Date(r.review) });
  }
  for (const s of env.data.settings ?? []) await tx.objectStore("settings").put(s.value, s.key);
  await tx.done;
}
