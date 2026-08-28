/**
 * The unlock gate (src/lib/unlocks.ts).
 *
 * Two halves, and the second is the important one:
 *  - with the flag OFF, no locked case is reachable from the trainer's set
 *    list, its pool, its counts or a `?group=` deep link, while the two
 *    cases the 4×4 course teaches stay reachable;
 *  - with the flags ON, exactly 60 more cases appear and nothing else moves
 *    (48 parity-embedded 4×4 + 12 one-look 5×5 last-two-edges).
 *
 * The flag is flipped for real here — `UNLOCKED` is the shipped object and
 * every trainer path re-reads it — rather than mocked, because a mocked
 * predicate would prove nothing about whether "unlock later" actually works.
 */
import { afterEach, describe, expect, test } from "vitest";

import { ALL_CASES } from "../src/data/algs";
import { RICH } from "../src/data/fullsets.rich.gen";
import type { UnlockKey } from "../src/lib/unlocks";
import {
  TAUGHT_444_CASES,
  TAUGHT_555_CASES,
  UNLOCKED,
  isLocked,
  lockReason,
} from "../src/lib/unlocks";
import {
  groupSize,
  parseGroupParam,
  pickCase,
  poolFor,
  selectionLabel,
  trainerGroups,
  trainerSets,
} from "../src/lib/trainer";

/** Every set key the app can name, locked or not. */
const LOCKED_SET_KEYS = ["444-oll", "444-pll"];
const ALL_SET_KEYS = [
  "cross-eo",
  "2look-oll-corners",
  "2look-pll-corners",
  "2look-pll-edges",
  "full-f2l",
  "full-oll",
  "full-pll",
  "444-parity",
  ...LOCKED_SET_KEYS,
  "555-l2e",
];

const lockedCases = () => ALL_CASES.filter((k) => isLocked(k));
const visibleKeys = () => trainerGroups().map((g) => g.key);

/** Every key, and what each ships as — asserted below, not assumed. */
const KEYS: UnlockKey[] = ["444-parity-embedded", "555-l2e-onelook"];
const SHIPPED: Record<UnlockKey, boolean> = {
  "444-parity-embedded": UNLOCKED["444-parity-embedded"],
  "555-l2e-onelook": UNLOCKED["555-l2e-onelook"],
};
const restore = () => {
  for (const k of KEYS) UNLOCKED[k] = SHIPPED[k];
};

/** Run `fn` with every unlock key forced to `on`, then put them all back. */
function withFlags<T>(on: boolean, fn: () => T): T {
  for (const k of KEYS) UNLOCKED[k] = on;
  try {
    return fn();
  } finally {
    restore();
  }
}
const locked = <T>(fn: () => T): T => withFlags(false, fn);
const unlocked = <T>(fn: () => T): T => withFlags(true, fn);

afterEach(() => {
  // A failed assertion inside a wrapper must not leave a flag flipped for
  // the next test.
  restore();
});

describe("444-parity-embedded, locked", () => {
  test("ships off — the tripwire; when you unlock a set, flip this too", () => {
    for (const k of KEYS) expect(SHIPPED[k], k).toBe(false);
    expect(lockReason("444-parity-embedded")).toMatch(/parity-embedded/);
    expect(lockReason("555-l2e-onelook")).toMatch(/one-look/);
  });

  test("exactly 48 cases are locked, and they are the parity-embedded ones", () => {
    locked(() => {
      const locked = lockedCases().filter((k) => k.puzzle === "4x4x4");
      expect(locked.length).toBe(48);
      for (const k of locked) {
        expect(k.puzzle).toBe("4x4x4");
        expect(k.id).toMatch(/^444\.(oll|pll)\./);
        expect(TAUGHT_444_CASES.has(k.id)).toBe(false);
      }
    });
  });

  test("the two taught 4×4 cases are not locked", () => {
    locked(() => {
      for (const id of TAUGHT_444_CASES) {
        const def = ALL_CASES.find((k) => k.id === id);
        expect(def, id).toBeDefined();
        expect(isLocked(def!), id).toBe(false);
      }
      // …even though one of them sits inside a group that *is* locked, which is
      // the whole reason isLocked(case) is keyed on the id and not the group.
      expect(isLocked("4x4pll-edges-only")).toBe(true);
    });
  });

  test("no locked set is offered, and the visible 4×4 set is the parity one", () => {
    locked(() => {
      expect(visibleKeys()).not.toContain("444-oll");
      expect(visibleKeys()).not.toContain("444-pll");
      expect(visibleKeys()).toContain("444-parity");

      const parity = trainerSets().find((s) => s.key === "444-parity")!;
      expect(parity.name).toBe("4×4 parity");
      expect(parity.cases.map((c) => c.id).sort()).toEqual([...TAUGHT_444_CASES].sort());
    });
  });

  test("group counts do not count locked cases", () => {
    locked(() => {
      expect(groupSize("444-parity")).toBe(2);
      for (const key of LOCKED_SET_KEYS) expect(groupSize(key), key).toBe(0);
      // The 3×3 sets are untouched by any of this.
      expect(groupSize("full-oll")).toBe(57);
      expect(groupSize("full-pll")).toBe(21);
    });
  });

  test("no locked case is reachable from any pool, from any selection", () => {
    locked(() => {
      const everything = poolFor(ALL_SET_KEYS);
      const lockedIds = new Set(lockedCases().map((k) => k.id));
      expect(everything.filter((c) => lockedIds.has(c.id))).toEqual([]);
      // Every visible set on its own, too — not just the union.
      for (const key of visibleKeys()) {
        for (const c of poolFor([key])) expect(isLocked(c), `${key}/${c.id}`).toBe(false);
      }
      expect(
        poolFor(["444-parity"])
          .map((c) => c.id)
          .sort(),
      ).toEqual([...TAUGHT_444_CASES].sort());
    });
  });

  test("a locked set cannot be selected by a ?group= deep link", () => {
    locked(() => {
      expect(parseGroupParam("444-oll")).toEqual([]);
      expect(parseGroupParam("444-oll,444-pll")).toEqual([]);
      // A link naming a locked set alongside a live one keeps only the live one.
      expect(parseGroupParam("444-oll,444-parity")).toEqual(["444-parity"]);
      // Selecting a locked key by hand still yields an empty pool.
      expect(poolFor(LOCKED_SET_KEYS)).toEqual([]);
      expect(selectionLabel(LOCKED_SET_KEYS)).toBe("none selected");
    });
  });

  test("the trainer can never deal a locked case", () => {
    locked(() => {
      const pool = poolFor(visibleKeys());
      let seed = 1;
      const random = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
      for (let i = 0; i < 2000; i++) {
        expect(isLocked(pickCase(pool, "balanced", undefined, random))).toBe(false);
      }
    });
  });
});

describe("555-l2e-onelook, locked", () => {
  test("exactly 12 of the 13 L2E cases are locked, and parity is the survivor", () => {
    locked(() => {
      const l2e = ALL_CASES.filter((k) => k.id.startsWith("555.l2e-"));
      expect(l2e.length).toBe(13);
      const hidden = l2e.filter((k) => isLocked(k));
      expect(hidden.length).toBe(12);
      for (const k of hidden) expect(TAUGHT_555_CASES.has(k.id), k.id).toBe(false);
      for (const id of TAUGHT_555_CASES) {
        const def = ALL_CASES.find((k) => k.id === id);
        expect(def, id).toBeDefined();
        expect(isLocked(def!), id).toBe(false);
      }
    });
  });

  test("the group stays visible with one case — the only question a 5×5 asks", () => {
    locked(() => {
      // Deliberately NOT hidden: a one-case set still drills "is this parity?".
      expect(visibleKeys()).toContain("555-l2e");
      expect(groupSize("555-l2e")).toBe(1);
      expect(poolFor(["555-l2e"]).map((c) => c.id)).toEqual([...TAUGHT_555_CASES]);
      const set = trainerSets().find((s) => s.key === "555-l2e")!;
      expect(set.name).toBe("5×5 edge parity");
    });
  });

  test("the surviving case carries the parity algorithm and a real cue", () => {
    const def = ALL_CASES.find((k) => k.id === "555.l2e-6")!;
    expect(def.algs.find((a) => a.primary)!.moves).toBe(
      "Rw U2 x Rw U2 Rw U2 3Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'",
    );
    // Recognition lives in the build-time rich file, not the lean shipped one.
    // It used to read "Last two edges (5×5)" — the same string on all thirteen,
    // which is why /reference showed thirteen tiles nobody could tell apart.
    expect(RICH["555.l2e-6"]!.recognition).toMatch(/UF/);
    const cues = new Set(
      Object.entries(RICH)
        .filter(([id]) => id.startsWith("555.l2e-"))
        .map(([, v]) => v.recognition),
    );
    expect(cues.size, "the other twelve still share one placeholder cue").toBeGreaterThan(1);
  });

  test("unlocking restores all 13", () => {
    unlocked(() => {
      expect(groupSize("555-l2e")).toBe(13);
      expect(poolFor(["555-l2e"]).length).toBe(13);
      for (const c of poolFor(["555-l2e"])) {
        expect(c.puzzle, c.id).toBe("5x5x5");
        expect(
          c.algs.some((a) => a.primary),
          c.id,
        ).toBe(true);
      }
    });
  });
});

describe("444-parity-embedded, the unlock path", () => {
  test("surfaces exactly 60 more cases", () => {
    const before = locked(() => poolFor(ALL_SET_KEYS).length);
    const after = unlocked(() => poolFor(ALL_SET_KEYS).length);
    expect(after - before).toBe(60);
    expect(unlocked(() => lockedCases().length)).toBe(0);
  });

  test("brings both sets back, named and counted", () => {
    unlocked(() => {
      expect(visibleKeys()).toContain("444-oll");
      expect(visibleKeys()).toContain("444-pll");
      expect(groupSize("444-oll")).toBe(27);
      expect(groupSize("444-pll")).toBe(22);
      // The visible parity set is unchanged by the unlock — the two cases
      // the course teaches stay their own set rather than dissolving into 49.
      expect(groupSize("444-parity")).toBe(2);
      expect(parseGroupParam("444-oll,444-pll")).toEqual(["444-oll", "444-pll"]);
      expect(poolFor(["444-oll"]).length).toBe(27);
      expect(poolFor(["444-pll"]).length).toBe(22);
    });
  });

  test("the 48 restored cases carry a verified primary algorithm", () => {
    // Guards the failure mode that makes "unlock later" not work: the data
    // going stale behind the flag. Every restored case must still resolve.
    unlocked(() => {
      const pool = poolFor(["444-oll", "444-pll"]);
      expect(pool.length).toBe(49);
      for (const c of pool) {
        expect(
          c.algs.some((a) => a.primary),
          c.id,
        ).toBe(true);
        expect(c.puzzle, c.id).toBe("4x4x4");
      }
    });
  });

  test("nothing outside the locked sets moves", () => {
    const before = locked(() => ({
      keys: visibleKeys().filter((k) => !k.startsWith("444-")),
      oll: groupSize("full-oll"),
      pll: groupSize("full-pll"),
      f2l: groupSize("full-f2l"),
      twoLook: poolFor(["2look-oll-corners", "2look-pll-corners", "2look-pll-edges"]).length,
    }));
    const after = unlocked(() => ({
      keys: visibleKeys().filter((k) => !k.startsWith("444-")),
      oll: groupSize("full-oll"),
      pll: groupSize("full-pll"),
      f2l: groupSize("full-f2l"),
      twoLook: poolFor(["2look-oll-corners", "2look-pll-corners", "2look-pll-edges"]).length,
    }));
    expect(after).toEqual(before);
  });

  test("the wrappers restore every flag afterwards", () => {
    for (const k of KEYS) expect(UNLOCKED[k], k).toBe(SHIPPED[k]);
    expect(locked(() => lockedCases().length)).toBe(60);
  });
});
