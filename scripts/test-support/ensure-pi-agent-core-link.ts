import { existsSync, mkdirSync, realpathSync, rmSync, symlinkSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { registerPiAgentCoreMock } from "./register-pi-agent-core-mock";

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

const hasPiAgentCorePackage = (path: string): boolean =>
	existsSync(join(path, "package.json"));

const ensureLink = () => {
	if (hasPiAgentCorePackage(linkPath)) return;
	rmSync(linkPath, { recursive: true, force: true });

	const source = resolvePiAgentCoreSource();
	if (!source) {
		registerPiAgentCoreMock();
		return;
	}

	mkdirSync(join(repoRoot, "node_modules/@earendil-works"), { recursive: true });
	symlinkSync(source, linkPath);
};

ensureLink();
