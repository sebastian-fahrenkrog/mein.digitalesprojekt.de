/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - duration parsing/formatting for time tracking.

const MAX_MINUTES = 24 * 60;

/**
 * Parse a user-entered duration into minutes.
 * Accepts "1:30", "1,5" / "1.5" (hours), "2" (hours), "90m", "2h", "1h 30m".
 * Returns null for anything unparsable or outside 1 minute .. 24 hours.
 */
export const parseDurationToMinutes = (input: string): number | null => {
  const value = input.trim().toLowerCase().replace(",", ".");
  if (!value) return null;

  let minutes: number | null = null;
  const clock = value.match(/^(\d+):([0-5]\d)$/);
  const units = value.match(/^(?:(\d+(?:\.\d+)?)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?$/);
  if (clock) {
    minutes = Number(clock[1]) * 60 + Number(clock[2]);
  } else if (/^\d+(\.\d+)?$/.test(value)) {
    minutes = Math.round(Number(value) * 60);
  } else if (units && (units[1] || units[2])) {
    minutes = Math.round(Number(units[1] ?? 0) * 60) + Number(units[2] ?? 0);
  }

  if (minutes === null || minutes < 1 || minutes > MAX_MINUTES) return null;
  return minutes;
};

/** Format minutes as "1:30 h" for display. */
export const formatMinutes = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours}:${String(rest).padStart(2, "0")} h`;
};

/** Format minutes as an editable value, e.g. "1:30". */
export const minutesToInput = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  return `${hours}:${String(minutes % 60).padStart(2, "0")}`;
};
