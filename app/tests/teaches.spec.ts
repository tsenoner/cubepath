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
import { describe, expect, test } from "vitest";
import { caseById } from "../src/data/algs";
import { PHASES } from "../src/data/phases";
import { lessonsInOrder } from "../src/lib/lessons";
import { teachingLesson } from "../src/lib/teaches";
import { lessonFiles } from "./lessons";

const lessons = await lessonsInOrder();
const phaseOf = new Map(lessons.map((l) => [l.id, l.data.phase]));

/** Every lesson listing each case, in course order — the map's raw input. */
const claims = new Map<string, string[]>();
for (const l of lessons)
  for (const id of l.data.algorithms) claims.set(id, [...(claims.get(id) ?? []), l.id]);

/**
 * Every lesson that merely PICTURES each case. Disjoint from `claims` by a
 * build-time check in `Lesson.astro`; kept separate here so the assertions
 * below can say that this half reaches attribution nowhere.
 */
const shown = new Map<string, string[]>();
for (const l of lessons)
  for (const id of l.data.shows) shown.set(id, [...(shown.get(id) ?? []), l.id]);

/** Where a case says it is taught. */
const home = async (id: string) => (await teachingLesson(caseById.get(id)!))?.id;

/**
 * The phases a lesson can carry. `CaseDef.phase` is one of these for the
 * curated cases and an opaque set tag ("full-pll") for the generated ones —
 * `ladders.ts` says so — and only the former is a claim a lesson can be held to.
 */
const course = new Set(PHASES.map((p) => p.key));

describe("case -> lesson attribution", () => {
  test("the collection is the whole lesson directory", () => {
    // Every loop below passes vacuously over `[]`, which is what a test sees
    // when the content store has not been synced (see tests/global-setup.ts).
    expect(lessons.map((l) => `${l.id}.mdx`).sort()).toEqual(lessonFiles());
  });

  test("every listed case resolves to a lesson that lists it", async () => {
    for (const [id, listedBy] of claims) {
      expect(listedBy, `${id} attributed outside the lessons that list it`).toContain(
        await home(id),
      );
    }
  });

  test("a case is taught in a lesson of its own phase", async () => {
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

  test("where two lessons of one phase both list a case, the earlier teaches it", async () => {
    // Strictly stronger than the phase gate above, which is kept for its
    // diagnostic: that one names the fix for the common failure, this one says
    // WHICH lesson of the right phase — the half a phase check cannot see, and
    // the regression that sank the first attempt at this fix. A `phaseWins()`
    // rule inside teaches.ts read "last in phase" for `beginner.righty` and
    // moved it from the lesson that teaches it to the one that reuses it.
    for (const [id, listedBy] of claims) {
      const phase = caseById.get(id)!.phase;
      if (!course.has(phase)) continue;
      const inPhase = listedBy.filter((l) => phaseOf.get(l) === phase);
      expect(await home(id), `${id}: not the earliest of ${inPhase.join(", ")}`).toBe(inPhase[0]);
    }
  });

  test("`shows` pictures a case without claiming to teach it", async () => {
    // The two fields were ONE, and that is how trimming yellow-cross to fix
    // `eo.hook`'s "Taught in" link also cut Dot and Hook out of the case list
    // on the lesson that draws them. Splitting them is only safe while this
    // half stays invisible to attribution, so: every `shows` id is a real case,
    // no lesson both teaches and shows the same one, and a case shown by a
    // lesson is never attributed to it unless it also teaches it.
    expect(shown.size, "no lesson uses `shows` — this gate has nothing to hold").toBeGreaterThan(0);
    for (const [id, showers] of shown) {
      expect(caseById.has(id), `${id} in \`shows\` is not a case id`).toBe(true);
      const teachers = claims.get(id) ?? [];
      for (const l of showers) {
        expect(teachers, `${l} both teaches and shows ${id}`).not.toContain(l);
        expect(await home(id), `${id} is attributed to ${l}, which only shows it`).not.toBe(l);
      }
    }
  });

  test("the cases more than one lesson lists", async () => {
    // A cheap double entry: a NEW double listing has to come through here and
    // be looked at, because the rules above only decide which of the claimants
    // wins, never whether listing it twice was right.
    const multi = [...claims].filter(([, v]) => v.length > 1).map(([k]) => k);
    expect(multi.sort()).toEqual(["444.edge-flip", "beginner.righty", "eo.line", "oll.27"]);

    // The three the derived rules above cannot reach, pinned by hand.
    // `eo.hook` and `eo.dot` are what this whole file exists for: Phase 1.5
    // algorithms that Phase 1's yellow-cross used to list. One listing each
    // now, so no rule above chooses between claimants — delist them from
    // Speed Tricks too and attribution falls through to the group edge, which
    // is the failure these two pins catch.
    expect(await home("eo.hook")).toBe("speed-tricks");
    expect(await home("eo.dot")).toBe("speed-tricks");
    // That group edge, working. It has to be a case NO lesson lists — `pll.aa`
    // stood here and is in full-pll's own `algorithms`, so it answered through
    // the exact edge and pinned nothing the tests above had not already. A
    // generated case's phase is a set tag, not a course phase, so the gates
    // skip it and `practice.groups` is the only thing left to answer.
    expect(claims.has("oll.1"), "oll.1 is listed now — pick another unlisted case").toBe(false);
    expect(await home("oll.1")).toBe("full-oll-overview");
  });
});
