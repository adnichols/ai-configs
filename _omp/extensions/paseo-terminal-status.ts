import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

type TerminalState = "running" | "idle" | "needs-input";

export default function paseoTerminalStatus(pi: ExtensionAPI): void {
  const { PASEO_TERMINAL_ID: terminalId, PASEO_ACTIVITY_TOKEN: token, PASEO_TERMINAL_ACTIVITY_URL: url } = process.env;
  if (!terminalId || !token || !url) return;

  // Child agents inherit the terminal environment but must not change the parent's status.
  const owner = process.env.PASEO_OMP_STATUS_OWNER;
  if (owner && owner !== String(process.pid)) return;
  process.env.PASEO_OMP_STATUS_OWNER = String(process.pid);

  let sending = false;
  let pending: TerminalState | null = null;

  function report(state: TerminalState): void {
    pending = state;
    if (sending) return;
    void flush();
  }

  async function flush(): Promise<void> {
    sending = true;
    while (pending) {
      const state = pending;
      pending = null;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 500);
      try {
        await fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ terminalId, token, state }),
          signal: controller.signal,
        });
      } catch {
        // Reporting must not interrupt OMP if Paseo stops or the terminal closes.
      } finally {
        clearTimeout(timeout);
      }
    }
    sending = false;
  }
  let idleCheck: NodeJS.Timeout | undefined;
  let idleCheckDelay = 25;
  let settledEventSeen = false;
  let agentActive = false;
  let blockedCount = 0;

  function block(): void {
    blockedCount += 1;
    report("needs-input");
  }

  function unblock(): void {
    blockedCount = Math.max(0, blockedCount - 1);
    if (blockedCount === 0 && agentActive) report("running");
  }

  function clearIdleCheck(): void {
    clearTimeout(idleCheck);
    idleCheck = undefined;
  }

  function checkIdle(ctx: { isIdle(): boolean }): void {
    idleCheck = undefined;
    if (settledEventSeen) return;
    if (ctx.isIdle()) {
      agentActive = false;
      blockedCount = 0;
      report("idle");
      return;
    }
    idleCheck = setTimeout(() => checkIdle(ctx), idleCheckDelay);
    idleCheck.unref?.();
    idleCheckDelay = Math.min(idleCheckDelay * 2, 250);
  }

  pi.on("session_start", (_event, ctx) => {
    agentActive = ctx.isIdle() === false;
    blockedCount = 0;
    report(agentActive ? "running" : "idle");
  });
  pi.on("session_switch", (_event, ctx) => {
    agentActive = ctx.isIdle() === false;
    blockedCount = 0;
    report(agentActive ? "running" : "idle");
  });
  pi.on("agent_start", () => {
    agentActive = true;
    blockedCount = 0;
    clearIdleCheck();
    report("running");
  });
  pi.on("agent_settled", () => {
    settledEventSeen = true;
    clearIdleCheck();
    agentActive = false;
    blockedCount = 0;
    report("idle");
  });
  // Older OMP does not emit agent_settled. Its final agent_end precedes the
  // isIdle transition, and intermediate ends can occur during retries.
  pi.on("agent_end", (event, ctx) => {
    if (settledEventSeen || event.willContinue) return;
    clearIdleCheck();
    idleCheckDelay = 25;
    idleCheck = setTimeout(() => checkIdle(ctx), 0);
    idleCheck.unref?.();
  });
  pi.on("tool_approval_requested", block);
  pi.on("tool_approval_resolved", unblock);
  pi.on("tool_execution_start", (event) => {
    if (event.toolName === "ask") block();
  });
  pi.on("tool_execution_end", (event) => {
    if (event.toolName === "ask") unblock();
  });
}
