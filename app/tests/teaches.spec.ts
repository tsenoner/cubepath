/**
 * Which lesson a case says it is "Taught in".
 *
 * Nothing tested this map, and that is how the Hook shipped wrong: `eo.hook`
 * carries the one-pass wide-f `f R U R' U' f'` and a cue saying front-right —
 * both Phase 1.5's — while yellow-cross (Phase 1) claimed it first and teaches
 * two passes of the narrow `F R U R' U' F'` held back-left. /reference showed
 * the Phase 1.5 row and linked the Phase 1 lesson, so a reader following the
 * site's own link landed somewhere that never prints the algorithm they came
 * from.
 *
 * The rule `teaches.ts` implements: EARLIEST claiming lesson wins, unless the
 * case names a phase and a claimant is in it, which wins instead — and among
 * equals the earliest still wins. That last clause is the one that bites: three
 * phase-1 lessons claim `beginner.righty`, so a rule of "any phase match wins"
 * silently becomes "LAST match wins" and moves righty from where it is taught
 * to where it is reused. Both halves are pinned below.
 */
import { describe, expect, test } from "vitest";
import { getCollection } from "astro:content";
import { ALL_CASES, caseById } from "../src/data/algs";
import { teachingLesson } from "../src/lib/teaches";
import { isLocked } from "../src/lib/unlocks";

/** Every lesson claiming each case, in course order — the map's raw input. */
async function claims(): Promise<Map<string, { id: string; phase: string }[]>> {
  const lessons = (await getCollection("lessons")).sort((a, b) => a.data.order - b.data.order);
  const out = new Map<string, { id: string; phase: string }[]>();
  for (const l of lessons)
    for (const id of l.data.algorithms)
      out.set(id, [...(out.get(id) ?? []), { id: l.id, phase: l.data.phase }]);
  return out;
}

describe("case -> lesson attribution", () => {
  test("the cases two lessons both claim, and where each lands", async () => {
    const multi = [...(await claims())].filter(([, v]) => v.length > 1).map(([k]) => k);
    // Seven, and the list is asserted so a NEW multi-claimed case has to come
    // through this test rather than pick up whichever rule happens to apply.
    expect(multi.sort()).toEqual([
      "444.edge-flip",
      "beginner.lefty",
      "beginner.righty",
      "eo.dot",
      "eo.hook",
      "eo.line",
      "oll.27",
    ]);
    const home = async (id: string) => (await teachingLesson(caseById.get(id)!))?.id;

    // The Hook and the Dot both carry Phase 1.5 algorithms — the wide-f, and
    // the chain whose second half is the wide-f — so they belong to the lesson
    // that teaches those, not to the one that first names the pattern.
    expect(await home("eo.hook")).toBe("speed-tricks");
    expect(await home("eo.dot")).toBe("speed-tricks");
    // ...and the Line does NOT move: its `F R U R' U' F'` is Phase 1's, and
    // Phase 1 is where it is taught. Same section on /reference, two homes.
    expect(await home("eo.line")).toBe("yellow-cross");

    // The regression guard. All three claimants are phase-1, so the case's
    // phase cannot break the tie and course order has to hold.
    expect(await home("beginner.righty")).toBe("white-corners");
    expect(await home("beginner.lefty")).toBe("white-corners");
    // Claimed by a phase-2 and a phase-3 lesson; the case is phase-2, which is
    // also the earlier one, so both rules agree.
    expect(await home("oll.27")).toBe("cfop-switch");
    expect(await home("444.edge-flip")).toBe("444-edge-pairing");
  });

  test("a single-claimed case is never touched by the phase rule", async () => {
    // The 15 `pll.*` cases are the reason the rule is guarded: their `phase`
    // ("full-pll") is a different vocabulary from any lesson's ("full-cfop"),
    // so a phase-EQUALITY rule applied unguarded would strand every one of
    // them. One claimant means course order, always.
    const claimed = await claims();
    for (const [id, v] of claimed) {
      if (v.length !== 1) continue;
      expect(await teachingLesson(caseById.get(id)!).then((t) => t?.id), id).toBe(v[0]!.id);
    }
    expect((await teachingLesson(caseById.get("pll.aa")!))?.id).toBe("full-pll");
  });

  test("every visible case that a lesson claims resolves to a real lesson", async () => {
    const claimed = await claims();
    for (const def of ALL_CASES) {
      if (isLocked(def) || !claimed.has(def.id)) continue;
      const home = await teachingLesson(def);
      expect(home, `${def.id} is claimed but resolves nowhere`).toBeTruthy();
      // And the lesson it names really does claim it — the phase rule must not
      // be able to hand a case to a lesson that never listed it.
      expect(
        claimed.get(def.id)!.map((c) => c.id),
        `${def.id} attributed to ${home!.id}, which does not list it`,
      ).toContain(home!.id);
    }
  });
});
