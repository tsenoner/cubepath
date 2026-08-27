/** Storage + SRS behavior on a real (fake) IndexedDB. */
import "fake-indexeddb/auto";
import { beforeEach, describe, expect, test } from "vitest";
import { IDBFactory } from "fake-indexeddb";

import { createEmptyCard } from "ts-fsrs";

import {
  _resetDBCache,
  allProgress,
  dueCards,
  exportBackup,
  forgetCards,
  getCard,
  importBackup,
  setStatus,
} from "../src/lib/db";
import { dueQueue, ensureCard, Rating, previewIntervals, review } from "../src/lib/srs";
import { caseById } from "../src/data/algs";

/** An id no build of the dataset has ever had — the orphan-card stand-in. */
const ORPHAN = "pll.u-a";

beforeEach(() => {
  // Fresh database per test.
  globalThis.indexedDB = new IDBFactory();
  _resetDBCache();
});

describe("progress", () => {
  test("status round-trips", async () => {
    await setStatus("pll.t", "learning");
    await setStatus("pll.y", "learned");
    const all = await allProgress();
    expect(all.map((p) => [p.caseId, p.status]).sort()).toEqual([
      ["pll.t", "learning"],
      ["pll.y", "learned"],
    ]);
  });

  test("review upgrades unseen to learning but never demotes learned", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    const statusOf = async (id: string) =>
      (await allProgress()).find((p) => p.caseId === id)?.status;

    // No progress entry yet → review marks the case "learning".
    await review("pll.t", Rating.Good, now);
    expect(await statusOf("pll.t")).toBe("learning");

    // A "learned" case stays learned after a review.
    await setStatus("pll.y", "learned");
    await review("pll.y", Rating.Good, now);
    expect(await statusOf("pll.y")).toBe("learned");
  });
});

describe("spaced repetition", () => {
  test("review schedules a card into the future and the due queue respects it", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    const card = await review("pll.t", Rating.Good, now);
    expect(card.due.getTime()).toBeGreaterThan(now.getTime());

    // Not due immediately after review…
    expect(await dueQueue(now)).toEqual([]);
    // …but due once its time arrives.
    expect(await dueQueue(new Date(card.due.getTime() + 1000))).toEqual(["pll.t"]);
  });

  test("Again schedules sooner than Easy", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    const again = await review("oll.27", Rating.Again, now);
    const easy = await review("oll.26", Rating.Easy, now);
    expect(again.due.getTime()).toBeLessThan(easy.due.getTime());
  });

  test("preview labels exist for all four grades", async () => {
    const labels = await previewIntervals("pll.t", new Date("2026-08-19T12:00:00Z"));
    expect(Object.keys(labels).sort()).toEqual(["Again", "Easy", "Good", "Hard"]);
  });

  test("setStatus alone leaves the queue empty; ensureCard seeds a due card", async () => {
    const now = new Date("2026-08-19T12:00:00Z");

    // Status is progress metadata — it must not create a review card…
    await setStatus("pll.t", "learning");
    expect(await dueQueue(now)).toEqual([]);

    // …ensureCard is what feeds the review queue, due immediately.
    await ensureCard("pll.t", now);
    expect(await dueQueue(now)).toEqual(["pll.t"]);

    // Grading pushes the card into the future.
    await review("pll.t", Rating.Good, now);
    expect(await dueQueue(now)).toEqual([]);

    // Re-seeding (e.g. cycling the status away and back) must not reset it.
    await ensureCard("pll.t", now);
    expect(await dueQueue(now)).toEqual([]);
  });
});

describe("backup", () => {
  test("export → import round-trips, reviving dates for the due index", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    await review("pll.t", Rating.Good, now);
    await setStatus("pll.t", "learning");

    const backup = await exportBackup();
    // Simulate a fresh device + JSON serialization (dates become strings).
    // Dropping the cached connection matters: without it the import would
    // silently reuse the old device's connection and test nothing.
    globalThis.indexedDB = new IDBFactory();
    _resetDBCache();
    await importBackup(JSON.parse(JSON.stringify(backup)));

    const card = await getCard("pll.t");
    expect(card).toBeDefined();
    expect(card!.due).toBeInstanceOf(Date);
    // The by-due index works after import — the revival regression guard.
    const due = await dueCards(new Date("2027-01-01T00:00:00Z"));
    expect(due.map((c) => c.caseId)).toEqual(["pll.t"]);
    expect((await allProgress())[0]!.status).toBe("learning");
  });

  test("import refuses foreign files", async () => {
    await expect(importBackup({ app: "not-cubepath" })).rejects.toThrow(/Not a Cubepath backup/);
  });

  test("import drops rows for cases the dataset no longer has, and says how many", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    const card = createEmptyCard(now);
    const { skipped } = await importBackup(
      {
        app: "cubepath",
        schemaVersion: 1,
        exportedAt: now.toISOString(),
        data: {
          progress: [
            { caseId: "pll.t", status: "learning", updatedAt: 0 },
            { caseId: ORPHAN, status: "learning", updatedAt: 0 },
          ],
          cards: [
            { ...card, caseId: "pll.t" },
            { ...card, caseId: ORPHAN },
          ],
          reviews: [],
          settings: [],
        },
      },
      (id) => caseById.has(id),
    );

    expect(skipped).toEqual([ORPHAN]);
    expect(await getCard(ORPHAN)).toBeUndefined();
    expect(await getCard("pll.t")).toBeDefined();
    expect((await allProgress()).map((p) => p.caseId)).toEqual(["pll.t"]);
  });

  test("import without a validator keeps every card (the default predicate)", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    const { skipped } = await importBackup({
      app: "cubepath",
      schemaVersion: 1,
      exportedAt: now.toISOString(),
      data: {
        progress: [],
        cards: [{ ...createEmptyCard(now), caseId: ORPHAN }],
        reviews: [],
        settings: [],
      },
    });
    expect(skipped).toEqual([]);
    expect(await getCard(ORPHAN)).toBeDefined();
  });
});

describe("orphan cards", () => {
  test("an unknown case id is purged from the queue, not merely skipped", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    await ensureCard(ORPHAN, now);
    await ensureCard("pll.t", now);
    await setStatus(ORPHAN, "learning");
    expect(caseById.has(ORPHAN)).toBe(false);
    expect((await dueQueue(now)).toSorted()).toEqual(["pll.t", ORPHAN]);

    // What nextReview() does: everything the dataset cannot resolve leaves the
    // store. Skipping alone dead-ends the queue, because grading re-persists it.
    const unknown = (await dueQueue(now)).filter((id) => !caseById.has(id));
    expect(unknown).toEqual([ORPHAN]);
    await forgetCards(unknown);

    expect(await dueQueue(now)).toEqual(["pll.t"]);
    expect(await getCard(ORPHAN)).toBeUndefined();
    // The progress row goes with it, or "Your cases" keeps showing the ghost.
    expect(await allProgress()).toEqual([]);
    // …and the live card's schedule is untouched.
    expect(await getCard("pll.t")).toBeDefined();
  });

  test("forgetCards on an empty list is a no-op", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    await ensureCard("pll.t", now);
    await forgetCards([]);
    expect(await dueQueue(now)).toEqual(["pll.t"]);
  });
});
