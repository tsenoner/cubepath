/**
 * Which lesson a case says it is "Taught in".
 *
 * `teaches.ts` is course order: the first lesson listing a case is its home.
 * That is only right if a lesson lists the cases whose ALGORITHM it teaches,
 * and nothing checked that — which is how the Hook shipped wrong. `eo.hook`
 * carries the one-pass wide-f `f R U R' U' f'` and a cue saying front-right,
 * both Phase 1.5's, while yellow-cross (Phase 1) listed it and teaches two
 * passes of the narrow `F R U R' U' F'` held back-left: a reader following the
 * site's own link landed somewhere that never prints the algorithm they came
 * from. The gate below turns the phase a case declares into a checked claim
 * about the lesson that teaches it. docs/DECISIONS.md § "The Hook's two holds".
 */
import { readdirSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { getCollection } from "astro:content";
import { caseById } from "../src/data/algs";
import { PHASES } from "../src/data/phases";
import { teachingLesson } from "../src/lib/teaches";

const lessons = (await getCollection("lessons")).sort((a, b) => a.data.order - b.data.order);
const phaseOf = new Map(lessons.map((l) => [l.id, l.data.phase]));

/** Every lesson listing each case, in course order — the map's raw input. */
const claims = new Map<string, string[]>();
for (const l of lessons)
  for (const id of l.data.algorithms) {
    const listedBy = claims.get(id);
    if (listedBy) listedBy.push(l.id);
    else claims.set(id, [l.id]);
  }

/** Where a case says it is taught. */
const home = async (id: string) => (await teachingLesson(caseById.get(id)!))?.id;

describe("case -> lesson attribution", () => {
  test("the collection is the whole lesson directory", () => {
    // Every loop below passes vacuously over `[]`, which is what a test sees
    // when the content store has not been synced (see tests/global-setup.ts).
    const onDisk = readdirSync(new URL("../src/content/lessons/", import.meta.url)).filter((f) =>
      f.endsWith(".mdx"),
    );
    expect(lessons.map((l) => `${l.id}.mdx`).sort()).toEqual(onDisk.sort());
  });

  test("every listed case resolves to a lesson that lists it", async () => {
    for (const [id, listedBy] of claims) {
      expect(listedBy, `${id} attributed outside the lessons that list it`).toContain(
        await home(id),
      );
    }
  });

  test("a case is taught in a lesson of its own phase", async () => {
    // The gate. `CaseDef.phase` is a course phase for the curated cases and an
    // opaque set tag ("full-pll") for the generated ones — `ladders.ts` says
    // so — and only the former is a claim a lesson can be held to.
    const course = new Set(PHASES.map((p) => p.key));
    for (const id of claims.keys()) {
      const phase = caseById.get(id)!.phase;
      if (!course.has(phase)) continue;
      const lesson = (await home(id))!;
      expect(
        phaseOf.get(lesson),
        `${id} is ${phase}'s but "Taught in" goes to ${lesson}: drop it from that lesson's algorithms or move the case`,
      ).toBe(phase);
    }
  });

  test("the cases more than one lesson lists, and where each lands", async () => {
    // Pinned so a new double listing has to come through here. Each of these
    // is taught once and REUSED later; course order is the right answer for
    // all four, and the gate above is what keeps it that way.
    const multi = [...claims].filter(([, v]) => v.length > 1).map(([k]) => k);
    expect(multi.sort()).toEqual(["444.edge-flip", "beginner.righty", "eo.line", "oll.27"]);
    expect(await home("444.edge-flip")).toBe("444-edge-pairing");
    expect(await home("beginner.righty")).toBe("white-corners");
    expect(await home("eo.line")).toBe("yellow-cross");
    expect(await home("oll.27")).toBe("cfop-switch");
    // The two the gate exists for: one listing each, and it is Speed Tricks —
    // same /reference section as the Line, a different home, both correct.
    expect(await home("eo.hook")).toBe("speed-tricks");
    expect(await home("eo.dot")).toBe("speed-tricks");
    // A generated case's phase is a set tag the gate skips; course order holds.
    expect(await home("pll.aa")).toBe("full-pll");
  });
});
