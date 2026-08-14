import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { OPENAI_CODEX_MODELS } from "@earendil-works/pi-ai/providers/openai-codex.models";
import { describe, expect, it } from "vitest";
import { FALLBACK_MODEL_ITEMS } from "../src/cursor-fallback-models.generated.js";

const require = createRequire(import.meta.url);
const packageJson = require("../package.json") as {
	version: string;
	dependencies: Record<string, string>;
	devDependencies: Record<string, string>;
	peerDependencies: Record<string, string>;
	bundledDependencies?: string[];
	overrides?: Record<string, string>;
};

type LockPackage = {
	version?: string;
	dependencies?: Record<string, string>;
};

// pnpm-lock.yaml splits package metadata into `packages:` (resolution/engines,
// version often encoded in the key without a `version:` field) and `snapshots:`
// (resolved dependencies). pnpm-lock also does not record the root package
// version (unlike npm's package-lock.json). This parser merges both sections
// into a name-keyed map with {version, dependencies}.
function parsePnpmLock(text: string): Map<string, LockPackage> {
	const packages = new Map<string, LockPackage>();
	const lines = text.split("\n");

	const collectSection = (startLine: string) => {
		let index = lines.findIndex((line) => line === startLine);
		if (index === -1) return;
		index += 1;

		let current: LockPackage | null = null;
		for (let i = index; i < lines.length; i++) {
			const line = lines[i];
			if (line === "") continue;
			if (/^\S/.test(line)) break; // next top-level section

			const keyMatch = line.match(/^  '(.+)':\s*$/);
			if (keyMatch) {
				current = { version: versionFromKey(keyMatch[1]) };
				packages.set(keyMatch[1], current);
				continue;
			}
			if (!current) continue;

			const versionMatch = line.match(/^    version: (.+)$/);
			if (versionMatch) {
				current.version = versionMatch[1];
				continue;
			}
			if (!/^    dependencies:$/.test(line)) continue;
			const dependencies: Record<string, string> = {};
			for (let j = i + 1; j < lines.length; j++) {
				const depLine = lines[j];
				if (/^      \S/.test(depLine)) {
					const depMatch = depLine.match(/^      ([^:]+): (.+)$/);
					if (depMatch) dependencies[depMatch[1].replace(/^'|'$/g, "")] = depMatch[2];
				} else {
					i = j - 1;
					break;
				}
			}
			current.dependencies = dependencies;
		}
	};

	collectSection("packages:");
	collectSection("snapshots:");
	return packages;
}

// Version from keys like '@cursor/sdk@1.0.23', '@connectrpc/connect-node@1.7.0(...)'
// or 'undici@5.29.0': the portion after '<name>@' up to the peer-suffix '('.
function versionFromKey(key: string): string | undefined {
	const base = key.split("(")[0]; // drop the peer-dependency suffix like (...)
	const atIndex = base.lastIndexOf("@");
	if (atIndex === -1 || atIndex === base.length - 1) return undefined;
	return base.slice(atIndex + 1) || undefined;
}

const LOCK = parsePnpmLock(readFileSync(join(process.cwd(), "pnpm-lock.yaml"), "utf8"));

const PI_PACKAGES = [
	"@earendil-works/pi-ai",
	"@earendil-works/pi-coding-agent",
	"@earendil-works/pi-tui",
] as const;

// Resolved versions of the root package's own dependencies from the `importers:`
// block. This is the pnpm analog of npm's top-level node_modules/<name> entry:
// when a tree contains several versions (e.g. peer-driven pi-ai 0.80.9 + 0.80.10),
// the root's declared version is the authoritative baseline.
const ROOT_RESOLVED = (() => {
	const resolved = new Map<string, string>();
	const lines = readFileSync(join(process.cwd(), "pnpm-lock.yaml"), "utf8").split("\n");
	const start = lines.findIndex((line) => line === "importers:");
	if (start !== -1) {
		let current: string | null = null;
		for (let i = start + 1; i < lines.length; i++) {
			const line = lines[i];
			if (line.startsWith("packages:")) break;
			if (line === "") continue;
			const keyMatch = line.match(/^      '(.+)':\s*$/);
			if (keyMatch) {
				current = keyMatch[1];
				continue;
			}
			if (current) {
				const versionMatch = line.match(/^        version: (.+)$/);
				if (versionMatch) {
					resolved.set(current, versionMatch[1]);
				}
			}
		}
	}
	return resolved;
})();

function lockPackage(packageName: string): LockPackage | undefined {
	let fallback: LockPackage | undefined;
	for (const [key, pkg] of LOCK) {
		if (!key.startsWith(`${packageName}@`)) continue;
		if (pkg.dependencies) return pkg; // snapshots entry carries resolved deps
		fallback ??= pkg;
	}
	return fallback;
}

function lockPackageVersion(packageName: string): string | undefined {
	const rootVersion = ROOT_RESOLVED.get(packageName);
	if (rootVersion) return rootVersion.split("(")[0]; // drop peer suffix e.g. 0.80.9(...)
	return lockPackage(packageName)?.version;
}

describe("package metadata cutover baselines", () => {
	it("keeps package and changelog release versions aligned with the pnpm lockfile", () => {
		const changelogVersion = readFileSync(join(process.cwd(), "CHANGELOG.md"), "utf8").match(/^## (\S+) /m)?.[1];

		expect(changelogVersion).toBe(packageJson.version);
		expect(readFileSync(join(process.cwd(), "pnpm-lock.yaml"), "utf8")).toContain("lockfileVersion:");
		// pnpm-lock.yaml records resolved versions rather than the root package
		// version; keep the package.json specifier aligned with the resolved lock.
		expect(lockPackageVersion("@cursor/sdk")).toBe(packageJson.dependencies["@cursor/sdk"]);
	});

	it("pins Cursor SDK exactly", () => {
		expect(packageJson.dependencies["@cursor/sdk"]).toBe("1.0.23");
		expect(lockPackageVersion("@cursor/sdk")).toBe("1.0.23");
	});

	it("keeps local agent ID policy aligned with the installed public string contract", () => {
		const sdkOptions = readFileSync(join(process.cwd(), "node_modules/@cursor/sdk/dist/esm/options.d.ts"), "utf8");

		expect(sdkOptions).toMatch(/export interface AgentOptions[\s\S]*?\bagentId\?: string;/);
	});

	it("pins the Node ConnectRPC transport required by Cursor SDK's Node seam", () => {
		const sdkTransportDts = readFileSync(
			join(process.cwd(), "node_modules/@cursor/sdk/dist/esm/transport.d.ts"),
			"utf8",
		);

		expect(sdkTransportDts).toContain("Node");
		expect(sdkTransportDts).toContain("`@connectrpc/connect-node`");
		expect(lockPackage("@cursor/sdk")?.dependencies?.["@connectrpc/connect-node"]).toMatch(/^1\.7\.0/);
		expect(packageJson.dependencies["@connectrpc/connect-node"]).toBeUndefined();
		expect(lockPackageVersion("@connectrpc/connect-node")).toBe("1.7.0");
	});

	it("keeps installed ConnectRPC transport siblings aligned", () => {
		expect(lockPackageVersion("@connectrpc/connect-node")).toBe("1.7.0");
		expect(lockPackageVersion("@connectrpc/connect-web")).toBe("1.7.0");
	});

	it("leaves the Cursor SDK transport dependency tree to pnpm resolution", () => {
		expect(packageJson.dependencies.undici).toBeUndefined();
		expect(packageJson.bundledDependencies).toBeUndefined();
		expect(packageJson.overrides).toBeUndefined();
		expect(lockPackage("@connectrpc/connect-node")?.dependencies?.["undici"]).toBe("5.29.0");
	});

	it("removes the obsolete sqlite override", () => {
		expect(packageJson.overrides?.sqlite3).toBeUndefined();
	});

	it("pins pi validation baselines", () => {
		for (const packageName of PI_PACKAGES) {
			expect(packageJson.devDependencies[packageName]).toBe("0.80.9");
			expect(lockPackageVersion(packageName)).toBe("0.80.9");
		}
	});

	it("tracks Pi 0.80.9 GPT-5.6 Codex metadata", () => {
		for (const modelId of ["gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra"] as const) {
			expect(OPENAI_CODEX_MODELS[modelId]).toMatchObject({
				contextWindow: 372000,
				maxTokens: 128000,
				thinkingLevelMap: { xhigh: "xhigh", max: "max", minimal: "low" },
			});
		}
	});

	it("keeps Grok UX examples aligned with the generated Cursor catalog", () => {
		const spec = readFileSync(join(process.cwd(), "docs/cursor-model-ux-spec.md"), "utf8");
		const grok = FALLBACK_MODEL_ITEMS.find((item) => item.id === "grok-4.5");

		expect(grok?.parameters?.map((parameter) => parameter.id)).toEqual(["effort", "fast"]);
		expect(FALLBACK_MODEL_ITEMS.some((item) => item.id === "grok-4.3")).toBe(false);
		expect(spec).toContain("### `grok-4.5`");
		expect(spec).not.toContain("grok-4.3");
	});

	it("keeps @earendil-works peer dependency ranges unpinned per pi package guidance", () => {
		for (const packageName of PI_PACKAGES) {
			expect(packageJson.peerDependencies[packageName]).toBe("*");
		}
	});
});
