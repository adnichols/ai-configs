import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { registerBeforeCompactHook } from "./src/hooks/before-compact";
import { registerPiVccCommand } from "./src/commands/pi-vcc";
import { registerVccRecallCommand } from "./src/commands/vcc-recall";
import { registerRecallTool } from "./src/tools/recall";
import { createContinuationCoordinator } from "./src/core/coordinator";

export * from "./src/core/continuation";
export * from "./src/core/continuation-protocol";
export * from "./src/core/coordinator";
export * from "./src/core/log-schema";

export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";

export default (pi: ExtensionAPI) => {
  const coordinator = createContinuationCoordinator(pi);
  (globalThis as any)[PI_VCC_LOAD_MARKER] = true;
  registerBeforeCompactHook(pi, coordinator);
  registerPiVccCommand(pi, coordinator);
  registerVccRecallCommand(pi);
  registerRecallTool(pi);
};
