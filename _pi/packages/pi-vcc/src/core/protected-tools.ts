const PROTECTED_TOOL_NAMES = new Set([
  "Agent",
  "get_subagent_result",
  "spawn_council",
  "read_council_stream",
  "plan-review",
  "todo",
]);

export const isProtectedToolName = (name: string): boolean =>
  PROTECTED_TOOL_NAMES.has(name) || /review|subagent|^Task/.test(name);
