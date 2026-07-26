import { describe, expect, it } from "bun:test";
import { isProtectedToolName } from "../src/core/protected-tools";

describe("protected task tools", () => {
  it("retains task-extension results during compaction", () => {
    expect(isProtectedToolName("TaskCreate")).toBe(true);
    expect(isProtectedToolName("TaskList")).toBe(true);
    expect(isProtectedToolName("TaskGet")).toBe(true);
    expect(isProtectedToolName("TaskUpdate")).toBe(true);
    expect(isProtectedToolName("TaskExecute")).toBe(true);
  });

  it("does not protect the removed legacy todo tool", () => {
    expect(isProtectedToolName("todo")).toBe(false);
  });
});
