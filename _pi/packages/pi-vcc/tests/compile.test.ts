import { describe, it, expect } from "bun:test";
import { compile } from "../src/core/summarize";
import {
  userMsg,
  assistantText,
  assistantWithToolCall,
} from "./fixtures";

describe("compile", () => {
  it("returns empty string for no messages", () => {
    expect(compile({ messages: [] })).toBe("");
  });

  it("produces hybrid output with header + brief transcript", () => {
    const r = compile({
      messages: [
        userMsg("Fix login bug"),
        assistantWithToolCall("Read", { path: "auth.ts" }),
        assistantText("Found the issue.\n1. Fix validation"),
      ],
    });
    expect(r).toContain("[Session Goal]");
    expect(r).toContain("Fix login bug");
    expect(r).toContain("---");
    expect(r).toContain("[user]\nFix login bug");
    expect(r).toContain('* Read "auth.ts"');
    expect(r).toContain("Found the issue.");
  });

  it("merges previous summary goals", () => {
    const r = compile({
      messages: [userMsg("New task")],
      previousSummary: "[Session Goal]\n- Original goal\n\n---\n\n[user]\nOriginal goal",
    });
    expect(r).toContain("- Original goal");
    expect(r).toContain("- New task");
  });

  it("appends brief transcript on merge", () => {
    const previousSummary = [
      "[Session Goal]\n- Original goal",
      "---",
      "[user]\nOriginal goal\n\n[assistant]\n* Read \"old.ts\"",
    ].join("\n\n");
    const r = compile({
      previousSummary,
      messages: [
        userMsg("Next step"),
        assistantWithToolCall("Read", { path: "new.ts" }),
      ],
    });
    expect(r).toContain('* Read "old.ts"');
    expect(r).toContain('* Read "new.ts"');
    expect(r).toContain("Next step");
  });

  it("outstanding context is volatile (fresh only)", () => {
    const previousSummary = "[Outstanding Context]\n- old blocker\n\n---\n\n[user]\nhi";
    const r = compile({
      previousSummary,
      messages: [userMsg("continue")],
    });
    expect(r).not.toContain("old blocker");
  });

  it("sanitizes previous summary skill markup during merge", () => {
    const previousSummary = [
      "[Session Goal]",
      "- Existing goal",
      "",
      "---",
      "",
      "[user]",
      '<skill name="debug">',
      "internal instructions",
      "</skill>",
      "Continue debugging.",
    ].join("\n");
    const r = compile({
      previousSummary,
      messages: [userMsg("Fix auth")],
    });
    expect(r).toContain("[skill: debug]");
    expect(r).not.toContain("internal instructions");
    expect(r).not.toContain("<skill");
  });

  it("dedupes files across merged summary categories", () => {
    const previousSummary = [
      "[Files And Changes]",
      "- Created: src/auth.ts, tests/auth.test.ts",
      "",
      "---",
      "",
      "[assistant]",
      '* Write "src/auth.ts"',
    ].join("\n");
    const r = compile({
      previousSummary,
      messages: [assistantWithToolCall("Edit", { file_path: "src/auth.ts" })],
    });
    expect(r).toContain("- Modified: src/auth.ts");
    expect(r).toContain("- Created: tests/auth.test.ts");
    expect(r).not.toContain("Created: src/auth.ts, tests/auth.test.ts");
  });

  it("drops previously injected recall notes from merged briefs", () => {
    const previousSummary = [
      "[Session Goal]",
      "- Fix auth",
      "",
      "---",
      "",
      "[assistant]",
      "Investigating auth.",
      "",
      "---",
      "",
      "Note: conversation history before this summary is searchable via `vcc_recall`. Use it to find details, results, or context that may have been truncated above.",
    ].join("\n");
    const r = compile({
      previousSummary,
      messages: [userMsg("Continue")],
    });
    expect(r).toContain("Investigating auth.");
    expect(r).not.toContain("searchable via `vcc_recall`");
  });

  it("caps long brief transcript with rolling window", () => {
    const longTranscript = Array.from({ length: 200 }, (_, i) =>
      `[user]\nmessage ${i}`
    ).join("\n\n");
    const previousSummary = `[Session Goal]\n- goal\n\n---\n\n${longTranscript}`;
    const r = compile({
      previousSummary,
      messages: [userMsg("latest")],
    });
    expect(r).toContain("earlier lines omitted");
    expect(r).toContain("latest");
  });

  it("wraps final compiled output", () => {
    const r = compile({
      messages: [userMsg("check final summary wrapping " + "word ".repeat(80))],
    });
    const maxLineLength = Math.max(...r.split("\n").map((line) => line.length));
    expect(maxLineLength).toBeLessThanOrEqual(120);
  });

  it("preserves wrapped header bullets across later merges", () => {
    const previousSummary = [
      "[Session Goal]",
      "- Investigate a very long operator-facing compaction behavior where continuation prompts should remain",
      "  silent after completed assistant turns but resume when interrupted mid-response",
      "",
      "---",
      "",
      "[user]",
      "Original request",
    ].join("\n");
    const r = compile({
      previousSummary,
      messages: [userMsg("New follow-up")],
    });
    expect(r).toMatch(/silent after\s+completed assistant turns/);
    expect(r).toContain("interrupted mid-response");
    expect(r).toContain("- New follow-up");
  });

  it("preserves wrapped file bullets across later merges", () => {
    const previousSummary = [
      "[Files And Changes]",
      "- Read: _pi/packages/pi-vcc/src/core/very-long-file-name-that-wrapped-before-the-next-compact.ts,",
      "  _pi/packages/pi-vcc/src/core/continued-file.ts",
      "",
      "---",
      "",
      "[assistant]",
      "* Read files",
    ].join("\n");
    const r = compile({
      previousSummary,
      messages: [assistantWithToolCall("Read", { path: "fresh.ts" })],
    });
    expect(r).toContain("very-long-file-name-that-wrapped-before-the-next-compact.ts");
    expect(r).toContain("continued-file.ts");
    expect(r).toContain("fresh.ts");
  });

  it("redacts secrets after wrapping-sensitive assembly", () => {
    const secret = "token=" + "a".repeat(160);
    const r = compile({
      messages: [userMsg(`run deploy with ${secret}`)],
    });
    expect(r).toContain("token [REDACTED]");
    expect(r).not.toContain("a".repeat(80));
    expect(Math.max(...r.split("\n").map((line) => line.length))).toBeLessThanOrEqual(120);
  });

  it("includes compact_context intent and replaces it on later compactions", () => {
    const first = compile({
      messages: [userMsg("Implement compaction")],
      compactionIntent: {
        source: "compact_context",
        reason: "finished phase",
        boundary: "subtask_complete",
        preserve: "keep phase evidence",
      },
    });
    expect(first).toContain("[Compaction Intent]");
    expect(first).toContain("reason=finished phase");
    expect(first).toContain("preserve=keep phase evidence");

    const second = compile({
      previousSummary: first,
      messages: [userMsg("Next phase")],
      compactionIntent: {
        source: "compact_context",
        reason: "after tests",
        boundary: "after_test_loop",
      },
    });
    expect(second).toContain("reason=after tests");
    expect(second).not.toContain("reason=finished phase");
  });

  it("does not prune the wrong result in mixed sibling tool batches", () => {
    const assistantWithSiblingCalls = {
      role: "assistant",
      content: [
        { type: "toolCall", id: "tc_unique", name: "bash", arguments: { command: "npm test" } },
        { type: "toolCall", id: "tc_dup_old", name: "Read", arguments: { path: "src/a.ts" } },
      ],
      api: "messages",
      provider: "anthropic",
      model: "test",
      usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
      timestamp: Date.now(),
      stopReason: "toolUse",
    } as any;
    const r = compile({
      messages: [
        userMsg("Run mixed tools"),
        assistantWithSiblingCalls,
        { role: "toolResult", toolName: "bash", toolCallId: "tc_unique", content: "tests failed uniquely", isError: true } as any,
        { role: "toolResult", toolName: "Read", toolCallId: "tc_dup_old", content: "old duplicate read", isError: true } as any,
        assistantWithToolCall("Read", { path: "src/a.ts" }, "tc_dup_new"),
        { role: "toolResult", toolName: "Read", toolCallId: "tc_dup_new", content: "latest read result", isError: false } as any,
      ],
    });
    expect(r).toContain("tests failed uniquely");
    expect(r).not.toContain("old duplicate read");
  });

  it("prunes older duplicate error results but keeps the latest evidence", () => {
    const r = compile({
      messages: [
        userMsg("Search duplicate output"),
        assistantWithToolCall("bash", { command: "rg auth" }, "tc_1"),
        { role: "toolResult", toolName: "bash", toolCallId: "tc_1", content: "old auth error", isError: true } as any,
        assistantWithToolCall("bash", { command: "rg auth" }, "tc_2"),
        { role: "toolResult", toolName: "bash", toolCallId: "tc_2", content: "latest auth error", isError: true } as any,
      ],
    });
    expect(r).not.toContain("old auth error");
    expect(r).toContain("latest auth error");
  });

  it("includes bashExecution session-evidenced commits", () => {
    const r = compile({
      messages: [
        userMsg("Commit from shell execution"),
        { role: "bashExecution", command: "git commit -m 'Fix compaction'", output: "[r-pi-compaction abc1234] Fix compaction\n 1 file changed\n _pi/extensions/percentage-compaction.ts", exitCode: 0 } as any,
      ],
    });
    expect(r).toContain("[Commits]");
    expect(r).toContain("abc1234: Fix compaction");
  });

  it("does not record false commits from patch index hashes", () => {
    const r = compile({
      messages: [
        userMsg("Show commit"),
        assistantWithToolCall("bash", { command: "git show abc1234" }, "tc_show"),
        { role: "toolResult", toolName: "bash", toolCallId: "tc_show", content: "commit 1111111111111111111111111111111111111111\nAuthor: Example\n\n    Fix real thing\n\ndiff --git a/a.ts b/a.ts\nindex 2222222..3333333 100644", isError: false } as any,
      ],
    });
    expect(r).toContain("1111111: Fix real thing");
    expect(r).not.toContain("2222222:");
    expect(r).not.toContain("3333333:");
  });

  it("pairs git command output by toolCallId in sibling tool batches", () => {
    const siblingGitAndRead = {
      role: "assistant",
      content: [
        { type: "toolCall", id: "tc_git", name: "bash", arguments: { command: "git commit -m 'Real commit'" } },
        { type: "toolCall", id: "tc_read", name: "Read", arguments: { path: "src/a.ts" } },
      ],
      api: "messages",
      provider: "anthropic",
      model: "test",
      usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
      timestamp: Date.now(),
      stopReason: "toolUse",
    } as any;
    const r = compile({
      messages: [
        userMsg("Commit with siblings"),
        siblingGitAndRead,
        { role: "toolResult", toolName: "Read", toolCallId: "tc_read", content: "deadbee is in source text", isError: false } as any,
        { role: "toolResult", toolName: "bash", toolCallId: "tc_git", content: "[r-pi-compaction abc1234] Real commit", isError: false } as any,
      ],
    });
    expect(r).toContain("abc1234: Real commit");
    expect(r).not.toContain("deadbee:");
  });

  it("does not record false commits from failed git output or command text", () => {
    const r = compile({
      messages: [
        userMsg("Failed git lookup"),
        assistantWithToolCall("bash", { command: "git show deadbee" }, "tc_bad"),
        { role: "toolResult", toolName: "bash", toolCallId: "tc_bad", content: "fatal: bad object deadbee", isError: true } as any,
        assistantWithToolCall("bash", { command: "git commit -m 'fix deadbee case'" }, "tc_msg"),
        { role: "toolResult", toolName: "bash", toolCallId: "tc_msg", content: "nothing to commit", isError: true } as any,
      ],
    });
    expect(r).not.toContain("[Commits]");
    expect(r).not.toContain("deadbee:");
  });

  it("includes bounded session-evidenced commits", () => {
    const r = compile({
      messages: [
        userMsg("Commit the change"),
        assistantWithToolCall("bash", { command: "git commit -m 'Add compaction nudges'" }, "tc_git"),
        { role: "toolResult", toolName: "bash", toolCallId: "tc_git", content: "[r-pi-compaction 45e93e8] Add compaction nudges\n 1 file changed\n _pi/extensions/percentage-compaction.ts", isError: false } as any,
      ],
    });
    expect(r).toContain("[Commits]");
    expect(r).toContain("45e93e8: Add compaction nudges");
    expect(r).toContain("_pi/extensions/percentage-compaction.ts");
  });
});
