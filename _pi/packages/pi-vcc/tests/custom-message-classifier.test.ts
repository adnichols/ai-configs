import { describe, expect, it } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isLegacyContinuationMessage, LEGACY_CONTINUATION_MESSAGE_TYPE } from "../src/core/custom-message-classifier";
import { loadAllMessages } from "../src/core/load-messages";

describe("legacy continuation classifier", () => {
	it("recognizes historical continuation messages", () => {
		expect(isLegacyContinuationMessage({ customType: LEGACY_CONTINUATION_MESSAGE_TYPE })).toBe(true);
	});

	it("does not create a runtime action for unrelated custom messages", () => {
		expect(isLegacyContinuationMessage({ customType: "vcc-recall" })).toBe(false);
		expect(isLegacyContinuationMessage(undefined)).toBe(false);
	});

	it("keeps historical records searchable while labeling them as inert", () => {
		const dir = mkdtempSync(join(tmpdir(), "pi-vcc-legacy-"));
		const sessionFile = join(dir, "session.jsonl");
		try {
			writeFileSync(sessionFile, `${JSON.stringify({
				type: "message",
				message: { role: "custom", customType: LEGACY_CONTINUATION_MESSAGE_TYPE, content: "old continuation" },
			})}\n`);
			const loaded = loadAllMessages(sessionFile, false);
			expect(loaded.rawMessages).toHaveLength(1);
			expect(loaded.rendered[0]).toMatchObject({ role: "legacy_continuation" });
			expect(loaded.rendered[0]?.summary).toContain("old continuation");
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});
});
