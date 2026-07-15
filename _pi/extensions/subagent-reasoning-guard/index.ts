import {
	CONFIG_DIR_NAME,
	type ExtensionAPI,
} from "@earendil-works/pi-coding-agent";

import { installSubagentReasoningGuard } from "./policy";

export * from "./policy";

export default function subagentReasoningGuard(pi: ExtensionAPI): void {
	installSubagentReasoningGuard(pi, CONFIG_DIR_NAME);
}
