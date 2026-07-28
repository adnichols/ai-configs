import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const COMPACTION_INSTRUCTIONS =
  '__PI_VCC_MANUAL_BYPASS__\n{"source":"compact_context","boundary":"after_test_loop","reason":"real-host active semantic boundary","resumePolicy":"active","attemptId":"actual-compact-context-attempt","requestId":"actual-compact-context-request"}';

export default function registerActualCompactContextTrigger(pi: ExtensionAPI) {
  let requested = false;

  pi.on("turn_end", (event, ctx) => {
    if (requested || event.message?.role !== "assistant") return;
    requested = true;
    ctx.compact({ customInstructions: COMPACTION_INSTRUCTIONS });
  });
}
