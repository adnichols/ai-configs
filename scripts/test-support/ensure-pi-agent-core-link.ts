import { existsSync, lstatSync, mkdirSync, realpathSync, symlinkSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const linkPath = join(repoRoot, "node_modules/@earendil-works/pi-agent-core");

const resolvePiAgentCoreSource = (): string | undefined => {
	const piExecutable = Bun.which("pi");
	if (!piExecutable) return undefined;
	const runtimeRoot = dirname(dirname(realpathSync(piExecutable)));
	const nested = join(
		runtimeRoot,
		"node_modules/@earendil-works/pi-agent-core",
	);
	if (existsSync(join(nested, "package.json"))) return nested;
	return undefined;
};

const ensureLink = () => {
	if (existsSync(linkPath)) {
		try {
			const stat = lstatSync(linkPath);
			if (stat.isSymbolicLink() || stat.isDirectory()) return;
		} catch {
			return;
		}
	}

	const source = resolvePiAgentCoreSource();
	if (!source) {
		throw new Error(
			"Unable to resolve @earendil-works/pi-agent-core for extension tests. Install Pi globally (brew install pi) or create node_modules/@earendil-works/pi-agent-core manually.",
		);
	}

	mkdirSync(join(repoRoot, "node_modules/@earendil-works"), { recursive: true });
	symlinkSync(source, linkPath);
};

ensureLink();
