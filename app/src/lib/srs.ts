/**
 * Spaced repetition over algorithm cases — a thin, typed layer on ts-fsrs.
 * One Card per case id; raw FSRS cards are what's persisted (v6-migration-safe).
 */
import { createEmptyCard, fsrs, Rating, type Card, type Grade } from "ts-fsrs";

import { dueCards, getCard, recordReview } from "./db";

const scheduler = fsrs();

export { Rating };

export interface ReviewPreview {
  /** Interval label per grade, e.g. { Again: "<10m", Good: "3d" }. */
  [grade: string]: string;
}

function intervalLabel(from: Date, due: Date): string {
  const mins = Math.round((due.getTime() - from.getTime()) / 60_000);
  if (mins < 60) return `${Math.max(mins, 1)}m`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d`;
  return `${Math.round(days / 30)}mo`;
}

/** What each answer button would schedule — shown on the buttons themselves. */
export async function previewIntervals(caseId: string, now: Date): Promise<ReviewPreview> {
  const card = (await getCard(caseId)) ?? { ...createEmptyCard(now), caseId };
  const preview = scheduler.repeat(card, now);
  const labels: ReviewPreview = {};
  for (const grade of [Rating.Again, Rating.Hard, Rating.Good, Rating.Easy] as Grade[]) {
    labels[Rating[grade]] = intervalLabel(now, preview[grade].card.due);
  }
  return labels;
}

/** Grade a case review and persist the resulting card + log atomically. */
export async function review(caseId: string, grade: Grade, now: Date): Promise<Card> {
  const existing = (await getCard(caseId)) ?? { ...createEmptyCard(now), caseId };
  const { card } = scheduler.next(existing, now, grade);
  const withId = { ...card, caseId };
  await recordReview(withId, grade, now);
  return card;
}

/** Case ids due for review, soonest first. */
export async function dueQueue(now: Date): Promise<string[]> {
  return (await dueCards(now)).map((c) => c.caseId);
}
