import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

export const EVAL_FILE_WRITE_BLOCK_REASON =
	"eval cannot write tracked files. Use edit for existing files, write for new files, bash for a committed lever. local:// and /tmp scratch are allowed.";

const WRITE_CALL =
	/(?:Bun\.write|(?<!\.)\bwrite)\s*\(\s*(['"`])([^'"`\n]*)\1|(?:Bun\.write|(?<!\.)\bwrite)\s*\(/g;
const PATHLIB_WRITE = /\.write_(?:text|bytes)\s*\(/g;
const PATHLIB_LITERAL_WRITE =
	/\bPath\s*\(\s*(['"`])([^'"`\n]+)\1\s*\)\s*\.write_(?:text|bytes)\s*\(/g;
const WRITEFILE_LINE = /^\s*%%writefile\b(?:\s+(\S+))?/gm;
const OPEN_WRITE =
	/\bopen\s*\(([^;]{0,240})['"](?:w|a|x|w\+|a\+|r\+|wb|ab|wt)['"]/g;
const FIRST_STRING = /(['"`])([^'"`\n]*)\1/;

function isScratchPath(path: string | undefined): boolean {
	if (!path) return false;
	const p = path.trim();
	if (p.includes("..") || p.includes("$") || p.includes("{")) return false;
	return (
		p.startsWith("local://") ||
		p.startsWith("/tmp/") ||
		p.startsWith("/var/folders/")
	);
}

function countMatches(pattern: RegExp, code: string): number {
	pattern.lastIndex = 0;
	return (code.match(pattern) ?? []).length;
}

export function evalCellFileWriteReason(code: string): string | undefined {
	const pathlibWrites = countMatches(PATHLIB_WRITE, code);
	if (pathlibWrites > 0) {
		PATHLIB_LITERAL_WRITE.lastIndex = 0;
		const literalPaths: string[] = [];
		let literal: RegExpExecArray | null;
		while ((literal = PATHLIB_LITERAL_WRITE.exec(code))) {
			literalPaths.push(literal[2] ?? "");
		}
		if (
			literalPaths.length !== pathlibWrites ||
			literalPaths.some((p) => !isScratchPath(p))
		) {
			return EVAL_FILE_WRITE_BLOCK_REASON;
		}
	}

	WRITEFILE_LINE.lastIndex = 0;
	let writefile: RegExpExecArray | null;
	while ((writefile = WRITEFILE_LINE.exec(code))) {
		if (!isScratchPath(writefile[1])) {
			return EVAL_FILE_WRITE_BLOCK_REASON;
		}
	}

	OPEN_WRITE.lastIndex = 0;
	let openMatch: RegExpExecArray | null;
	while ((openMatch = OPEN_WRITE.exec(code))) {
		const first = FIRST_STRING.exec(openMatch[1] ?? "");
		if (!isScratchPath(first?.[2])) {
			return EVAL_FILE_WRITE_BLOCK_REASON;
		}
	}

	WRITE_CALL.lastIndex = 0;
	let match: RegExpExecArray | null;
	while ((match = WRITE_CALL.exec(code))) {
		if (!isScratchPath(match[2])) {
			return EVAL_FILE_WRITE_BLOCK_REASON;
		}
	}
	return undefined;
}

export default function evalNoFileWrites(pi: ExtensionAPI): void {
	pi.on("tool_call", async (event) => {
		if (event.toolName !== "eval") return;
		const code = typeof event.input?.code === "string" ? event.input.code : "";
		const reason = evalCellFileWriteReason(code);
		if (reason) return { block: true, reason };
		return undefined;
	});
}
