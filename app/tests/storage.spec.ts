/** Storage + SRS behavior on a real (fake) IndexedDB. */
import "fake-indexeddb/auto";
import { beforeEach, describe, expect, test } from "vitest";
import { IDBFactory } from "fake-indexeddb";

import {
  _resetDBCache,
  allProgress,
  dueCards,
  exportBackup,
  getCard,
  importBackup,
  setStatus,
} from "../src/lib/db";
import { dueQueue, Rating, previewIntervals, review } from "../src/lib/srs";

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
});

describe("backup", () => {
  test("export → import round-trips, reviving dates for the due index", async () => {
    const now = new Date("2026-08-19T12:00:00Z");
    await review("pll.t", Rating.Good, now);
    await setStatus("pll.t", "learning");

    const backup = await exportBackup();
    // Simulate a fresh device + JSON serialization (dates become strings).
    globalThis.indexedDB = new IDBFactory();
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
});
