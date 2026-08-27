import { describe, expect, test } from "bun:test";
import {
  MARKER,
  PIN,
  REMINDER_TYPE,
  STATE_TYPE,
  latestMatchingEntry,
  parseState,
  reduceEvent,
  reminderPayload,
} from "../extensions/adn-mode.ts";

function throughPhase(): number {
  const i = process.argv.indexOf("--through");
  if (i === -1) return 8;
  return Number(String(process.argv[i + 1] ?? "p8").replace(/^p/, "")) || 8;
}

const RUN = throughPhase() >= 2;

describe.skipIf(!RUN)("adn-mode extension", () => {
  test("marker and pin", () => {
    expect(MARKER).toContain(PIN);
    expect(MARKER).toBe(`ADN_RUNTIME_MARKER:extension-adn-mode:${PIN}`);
  });

  test("session_switch new resets enabled false", () => {
    const next = reduceEvent({ enabled: true }, {
      type: "session_switch",
      reason: "new",
      sessionId: "s2",
      generation: 1,
    });
    expect(next.enabled).toBe(false);
    expect(next.sessionId).toBe("s2");
    expect(next.generation).toBe(1);
  });

  test("resume restores latest matching session and generation", () => {
    const branch = [
      { customType: STATE_TYPE, details: { schemaVersion: 1, sessionId: "s1", generation: 1, enabled: false } },
      { customType: STATE_TYPE, details: { schemaVersion: 1, sessionId: "s1", generation: 1, enabled: true } },
      { customType: STATE_TYPE, details: { schemaVersion: 1, sessionId: "other", generation: 1, enabled: false } },
    ];
    const restored = parseState(latestMatchingEntry(branch, STATE_TYPE, "s1", 1)?.details);
    const next = reduceEvent({ enabled: false }, {
      type: "session_switch",
      reason: "resume",
      sessionId: "s1",
      generation: 1,
      branch,
    });
    expect(restored?.enabled).toBe(true);
    expect(next.enabled).toBe(true);
  });

  test("resume without matching entry stays off", () => {
    const next = reduceEvent({ enabled: true }, {
      type: "session_switch",
      reason: "resume",
      sessionId: "s1",
      generation: 1,
      branch: [],
    });
    expect(next.enabled).toBe(false);
  });

  test("branch tree compact restore latest matching entry", () => {
    const branch = [{ customType: STATE_TYPE, details: { schemaVersion: 1, sessionId: "s1", generation: 1, enabled: true } }];
    for (const reason of ["branch", "tree", "compact"] as const) {
      const next = reduceEvent({ enabled: false }, { type: reason, sessionId: "s1", generation: 1, branch });
      expect(next.enabled).toBe(true);
    }
  });

  test("session_start reconstructs matching entry", () => {
    const branch = [{ customType: STATE_TYPE, details: { schemaVersion: 1, sessionId: "s1", generation: 2, enabled: true } }];
    const next = reduceEvent({}, { type: "session_start", sessionId: "s1", generation: 2, branch });
    expect(next.enabled).toBe(true);
    expect(next.generation).toBe(2);
  });

  test("reminder is hidden with marker", () => {
    const payload = reminderPayload({ schemaVersion: 1, sessionId: "s1", generation: 1, enabled: true });
    expect(payload.customType).toBe(REMINDER_TYPE);
    expect(payload.display).toBe(false);
    expect(payload.content).toBe("");
    expect((payload.details as { marker: string }).marker).toContain(MARKER);
  });

  test("command last toggle wins", () => {
    const on = reduceEvent({ enabled: false }, { type: "command", enabled: true, sessionId: "s1", generation: 1 });
    const off = reduceEvent(on, { type: "command", enabled: false, sessionId: "s1", generation: 1 });
    expect(off.enabled).toBe(false);
  });
});
