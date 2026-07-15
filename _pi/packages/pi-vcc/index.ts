import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { registerBeforeCompactHook } from "./src/hooks/before-compact";
import { registerPiVccCommand } from "./src/commands/pi-vcc";
import { registerVccRecallCommand } from "./src/commands/vcc-recall";
import { registerRecallTool } from "./src/tools/recall";
import { createContinuationCoordinator, type ContinuationCoordinator } from "./src/core/coordinator";
import { CONTINUATION_PROTOCOL_NAME, CONTINUATION_PROTOCOL_VERSION } from "./src/core/continuation-protocol";

export * from "./src/core/continuation";
export * from "./src/core/continuation-protocol";
export * from "./src/core/coordinator";
export * from "./src/core/custom-message-classifier";
export * from "./src/core/log-schema";

export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";
export interface PiVccOwnerRecord {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: typeof CONTINUATION_PROTOCOL_VERSION;
  status: "initializing" | "active";
  coordinator?: ContinuationCoordinator;
  createdAt: number;
}

const owner = () =>
  (globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER] as
    | PiVccOwnerRecord
    | undefined;

export default (pi: ExtensionAPI) => {
  const existing = owner();
  if (
    existing?.protocol === CONTINUATION_PROTOCOL_NAME &&
    existing.version === CONTINUATION_PROTOCOL_VERSION
  ) return;
  if (existing !== undefined) {
    throw new Error("Conflicting pi-vcc coordinator owner is already registered");
  }

  const lease: PiVccOwnerRecord = {
    protocol: CONTINUATION_PROTOCOL_NAME,
    version: CONTINUATION_PROTOCOL_VERSION,
    status: "initializing",
    createdAt: Date.now(),
  };
  (globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER] = lease;

  let coordinator: ContinuationCoordinator | undefined;
  try {
    // Coordinator construction registers lifecycle handlers, so the process-wide
    // lease must exist before construction begins.
    coordinator = createContinuationCoordinator(pi, {
      onSessionReplacement: () => {
        coordinator?.dispose();
        if (owner() === lease) {
          delete (globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER];
        }
      },
    });
    registerBeforeCompactHook(pi, coordinator);
    registerPiVccCommand(pi, coordinator);
    registerVccRecallCommand(pi);
    registerRecallTool(pi);
    lease.coordinator = coordinator;
    lease.status = "active";
  } catch (error) {
    coordinator?.dispose();
    if (owner() === lease) {
      delete (globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER];
    }
    throw error;
  }
};
