/**
 * The unlock gate (src/lib/unlocks.ts).
 *
 * Two halves, and the second is the important one:
 *  - with the flag OFF, no locked case is reachable from the trainer's set
 *    list, its pool, its counts or a `?group=` deep link, while the two
 *    cases the 4×4 course teaches stay reachable;
 *  - with the flag ON, exactly 48 more cases appear and nothing else moves.
 *
 * The flag is flipped for real here — `UNLOCKED` is the shipped object and
 * every trainer path re-reads it — rather than mocked, because a mocked
 * predicate would prove nothing about whether "unlock later" actually works.
 */
import { afterEach, describe, expect, test } from "vitest";

import { ALL_CASES } from "../src/data/algs";
import { TAUGHT_444_CASES, UNLOCKED, isLocked, lockReason } from "../src/lib/unlocks";
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

const SHIPPED = UNLOCKED["444-parity-embedded"];

/** Run `fn` with `444-parity-embedded` forced to `on`, then put it back. */
function withFlag<T>(on: boolean, fn: () => T): T {
  UNLOCKED["444-parity-embedded"] = on;
  try {
    return fn();
  } finally {
    UNLOCKED["444-parity-embedded"] = SHIPPED;
  }
}
const locked = <T>(fn: () => T): T => withFlag(false, fn);
const unlocked = <T>(fn: () => T): T => withFlag(true, fn);

afterEach(() => {
  // A failed assertion inside a wrapper must not leave the flag flipped for
  // the next test.
  UNLOCKED["444-parity-embedded"] = SHIPPED;
});

describe("444-parity-embedded, locked", () => {
  test("ships off — the tripwire; when you unlock the set, flip this too", () => {
    expect(SHIPPED).toBe(false);
    expect(lockReason("444-parity-embedded")).toMatch(/parity-embedded/);
  });

  test("exactly 48 cases are locked, and they are the parity-embedded ones", () => {
    locked(() => {
      const locked = lockedCases();
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

describe("444-parity-embedded, the unlock path", () => {
  test("surfaces exactly 48 more cases", () => {
    const before = locked(() => poolFor(ALL_SET_KEYS).length);
    const after = unlocked(() => poolFor(ALL_SET_KEYS).length);
    expect(after - before).toBe(48);
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

  test("nothing outside the 4×4 sets moves", () => {
    const before = locked(() => ({
      keys: visibleKeys().filter((k) => !k.startsWith("444-")),
      oll: groupSize("full-oll"),
      pll: groupSize("full-pll"),
      f2l: groupSize("full-f2l"),
      l2e: groupSize("555-l2e"),
      twoLook: poolFor(["2look-oll-corners", "2look-pll-corners", "2look-pll-edges"]).length,
    }));
    const after = unlocked(() => ({
      keys: visibleKeys().filter((k) => !k.startsWith("444-")),
      oll: groupSize("full-oll"),
      pll: groupSize("full-pll"),
      f2l: groupSize("full-f2l"),
      l2e: groupSize("555-l2e"),
      twoLook: poolFor(["2look-oll-corners", "2look-pll-corners", "2look-pll-edges"]).length,
    }));
    expect(after).toEqual(before);
  });

  test("the wrappers restore the flag afterwards", () => {
    expect(UNLOCKED["444-parity-embedded"]).toBe(SHIPPED);
    expect(locked(() => lockedCases().length)).toBe(48);
  });
});
