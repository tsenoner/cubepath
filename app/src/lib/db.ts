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

/**
 * A lesson the learner has finished. Keyed by the content-collection slug, so
 * an entry outlives a re-order of the ladder but not a rename of the file.
 */
export interface LessonProgressEntry {
  slug: string;
  completedAt: number;
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
  lessons: { key: string; value: LessonProgressEntry };
}

const DB_NAME = "cubepath";
/**
 * v2 added the `lessons` store. Bumping is safe in both directions that matter:
 * an existing v1 database gains the store through `upgrade`, and a v1 backup
 * imports unchanged because its envelope simply carries no `lessons` array.
 */
const DB_VERSION = 2;

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
      if (oldVersion < 2) {
        db.createObjectStore("lessons", { keyPath: "slug" });
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

export async function allProgress(): Promise<ProgressEntry[]> {
  return (await getDB()).getAll("progress");
}

export async function setStatus(caseId: string, status: CaseStatus): Promise<void> {
  await (await getDB()).put("progress", { caseId, status, updatedAt: Date.now() });
}

// ── Lesson progress ────────────────────────────────────────

/**
 * The course had no "where am I" signal at all: 25 lessons rendered as 25
 * identical links, and the home page CTA pointed at lesson one on your
 * twentieth visit. These three functions are the whole progress layer — the
 * home page reads them, `LessonMeta.astro` writes them. Client-side only, so
 * the static build is untouched and it keeps working offline.
 */
async function allLessonProgress(): Promise<LessonProgressEntry[]> {
  return (await getDB()).getAll("lessons");
}

/** Completed slugs as a set — what every caller actually wants. */
export async function completedLessons(): Promise<Set<string>> {
  return new Set((await allLessonProgress()).map((l) => l.slug));
}

/**
 * Idempotent: re-reading a lesson you have already finished keeps the original
 * `completedAt`, so "first finished on" stays true.
 */
export async function markLessonComplete(slug: string): Promise<void> {
  const db = await getDB();
  // One transaction, so the read-then-write cannot interleave with a second
  // tab doing the same and reset an older completedAt to now.
  const tx = db.transaction("lessons", "readwrite");
  const store = tx.objectStore("lessons");
  if (!(await store.get(slug))) await store.put({ slug, completedAt: Date.now() });
  await tx.done;
}

/** Persist a graded review atomically: card state + log entry + progress. */
export async function recordReview(
  card: Card & { caseId: string },
  rating: number,
  when: Date,
): Promise<void> {
  const db = await getDB();
  const tx = db.transaction(["cards", "reviews", "progress"], "readwrite");
  const progress = tx.objectStore("progress");
  // Reviewing implies at least "learning" — but never demotes "learned".
  const existing = await progress.get(card.caseId);
  const status: CaseStatus =
    existing && existing.status !== "unseen" ? existing.status : "learning";
  await Promise.all([
    tx.objectStore("cards").put(card),
    tx.objectStore("reviews").add({ caseId: card.caseId, rating, review: when }),
    progress.put({ caseId: card.caseId, status, updatedAt: Date.now() }),
    tx.done,
  ]);
}

/** Write a card into the cards store only — no review log, no progress change (SRS seeding). */
export async function putCard(card: Card & { caseId: string }): Promise<void> {
  await (await getDB()).put("cards", card);
}

export async function getCard(caseId: string): Promise<(Card & { caseId: string }) | undefined> {
  return (await getDB()).get("cards", caseId);
}

/**
 * Drop cards + progress rows for case ids the dataset no longer has.
 *
 * A card outlives its case whenever an id is renamed upstream or a backup from
 * an older build is imported. Merely skipping such a card dead-ends the review
 * queue, because grading re-persists it — it has to leave the store.
 */
export async function forgetCards(caseIds: string[]): Promise<void> {
  if (caseIds.length === 0) return;
  const db = await getDB();
  const tx = db.transaction(["cards", "progress"], "readwrite");
  await Promise.all([
    ...caseIds.flatMap((id) => [
      tx.objectStore("cards").delete(id),
      tx.objectStore("progress").delete(id),
    ]),
    tx.done,
  ]);
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
    /** Added in schema v2. Absent in every v1 backup — read it defensively. */
    lessons?: LessonProgressEntry[];
  };
}

export async function exportBackup(): Promise<BackupEnvelope> {
  const db = await getDB();
  const [progress, cards, reviews, lessons, settingKeys] = await Promise.all([
    db.getAll("progress"),
    db.getAll("cards"),
    db.getAll("reviews"),
    db.getAll("lessons"),
    db.getAllKeys("settings"),
  ]);
  const settings = await Promise.all(
    settingKeys.map(async (key) => ({ key, value: await db.get("settings", key) })),
  );
  return {
    app: "cubepath",
    schemaVersion: DB_VERSION,
    exportedAt: new Date().toISOString(),
    data: { progress, cards, reviews, settings, lessons },
  };
}

/**
 * Restore a backup, dropping rows whose case this build no longer knows.
 *
 * Import is the main path by which an orphan card enters the store: a backup
 * from an older build carries ids that were since renamed or retired, and an
 * orphan in the review queue is a case with no diagram, no name and no
 * algorithm. `isKnownCase` is injected so db.ts stays free of the dataset;
 * the returned ids are reported to the user rather than silently swallowed.
 */
export async function importBackup(
  raw: unknown,
  isKnownCase: (caseId: string) => boolean = () => true,
): Promise<{ skipped: string[] }> {
  const env = raw as BackupEnvelope;
  if (env?.app !== "cubepath" || !env.data) throw new Error("Not a Cubepath backup file");
  if (env.schemaVersion > DB_VERSION) {
    throw new Error("Backup was made by a newer version of Cubepath");
  }
  const skipped = new Set<string>();
  const db = await getDB();
  const tx = db.transaction(["progress", "cards", "reviews", "settings", "lessons"], "readwrite");
  // Queue everything without awaiting each request — IndexedDB executes
  // requests of one transaction in order, so the clears run before the puts.
  const ops: Promise<unknown>[] = [
    tx.objectStore("progress").clear(),
    tx.objectStore("cards").clear(),
    tx.objectStore("reviews").clear(),
    tx.objectStore("settings").clear(),
    tx.objectStore("lessons").clear(),
  ];
  for (const p of env.data.progress ?? []) {
    if (!isKnownCase(p.caseId)) {
      skipped.add(p.caseId);
      continue;
    }
    ops.push(tx.objectStore("progress").put(p));
  }
  for (const c of env.data.cards ?? []) {
    if (!isKnownCase(c.caseId)) {
      skipped.add(c.caseId);
      continue;
    }
    // Revive dates: the by-due index needs real Date objects (ts-fsrs itself
    // tolerates ISO strings, which would silently break the due queue).
    ops.push(
      tx.objectStore("cards").put({
        ...c,
        due: new Date(c.due),
        // Omitted, not `undefined`: exactOptionalPropertyTypes distinguishes them.
        ...(c.last_review ? { last_review: new Date(c.last_review) } : {}),
      }),
    );
  }
  for (const r of env.data.reviews ?? []) {
    ops.push(tx.objectStore("reviews").add({ ...r, review: new Date(r.review) }));
  }
  for (const s of env.data.settings ?? []) ops.push(tx.objectStore("settings").put(s.value, s.key));
  // Lesson slugs are not case ids — `isKnownCase` does not apply. A slug this
  // build no longer has is inert: nothing ever looks it up.
  for (const l of env.data.lessons ?? []) ops.push(tx.objectStore("lessons").put(l));
  await Promise.all([...ops, tx.done]);
  return { skipped: [...skipped] };
}
