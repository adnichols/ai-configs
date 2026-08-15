import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { registerBeforeCompactHook } from "./src/hooks/before-compact";
import { registerPiVccCommand } from "./src/commands/pi-vcc";
import { registerVccRecallCommand } from "./src/commands/vcc-recall";
import { registerRecallTool } from "./src/tools/recall";

export * from "./src/core/custom-message-classifier";

export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";

interface PiVccOwnerRecord {
	status: "active";
	createdAt: number;
}

const owner = () =>
	(globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER] as PiVccOwnerRecord | undefined;

export default (pi: ExtensionAPI) => {
	const existing = owner();
	if (existing !== undefined) return;

	const lease: PiVccOwnerRecord = { status: "active", createdAt: Date.now() };
	(globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER] = lease;

	try {
		registerBeforeCompactHook(pi);
		registerPiVccCommand(pi);
		registerVccRecallCommand(pi);
		registerRecallTool(pi);
		pi.on("session_shutdown", () => {
			if (owner() === lease) delete (globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER];
		});
	} catch (error) {
		if (owner() === lease) delete (globalThis as Record<string, unknown>)[PI_VCC_LOAD_MARKER];
		throw error;
	}
};
