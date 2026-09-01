import { describe, expect, test } from "bun:test";
import evalNoFileWrites, {
	EVAL_FILE_WRITE_BLOCK_REASON,
	evalCellFileWriteReason,
} from "../_omp/extensions/eval-no-file-writes";

describe("evalCellFileWriteReason", () => {
	test("allows analysis cells", () => {
		expect(
			evalCellFileWriteReason(
				"from pathlib import Path\ntext = Path('cli.rs').read_text()\nprint(len(text))",
			),
		).toBeUndefined();
	});

	test("allows local:// and tmp scratch writes", () => {
		expect(evalCellFileWriteReason('write("local://plan.md", body)')).toBeUndefined();
		expect(evalCellFileWriteReason("write('/tmp/probe.json', data)")).toBeUndefined();
		expect(evalCellFileWriteReason("Path('/tmp/probe.txt').write_text(src)")).toBeUndefined();
		expect(
			evalCellFileWriteReason('Path("/var/folders/xx/y/probe.txt").write_bytes(data)'),
		).toBeUndefined();
		expect(evalCellFileWriteReason("open('/tmp/probe.txt', 'w').write(src)")).toBeUndefined();
	});

	test("allows a repo read beside a chained tmp write", () => {
		expect(
			evalCellFileWriteReason(
				"text = Path('cli.rs').read_text()\nPath('/tmp/probe.txt').write_text(text)",
			),
		).toBeUndefined();
	});

	test("blocks pathlib and repo prelude writes", () => {
		const cell = `from pathlib import Path
p=Path('/Users/anichols/.herdr/worktrees/heddle/nod-1633/cli.rs')
p.write_text(text)`;
		expect(evalCellFileWriteReason(cell)).toBe(EVAL_FILE_WRITE_BLOCK_REASON);
		expect(evalCellFileWriteReason("Path('cli.rs').write_text(src)")).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
		expect(evalCellFileWriteReason("open('src/app.ts', 'w')")).toBe(EVAL_FILE_WRITE_BLOCK_REASON);
		expect(evalCellFileWriteReason("p.write_text(src)")).toBe(EVAL_FILE_WRITE_BLOCK_REASON);
		expect(
			evalCellFileWriteReason(
				"Path('/tmp/a.txt').write_text(a)\nPath('cli.rs').write_text(b)",
			),
		).toBe(EVAL_FILE_WRITE_BLOCK_REASON);
		expect(evalCellFileWriteReason('write("/Users/anichols/code/heddle/cli.rs", src)')).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
		expect(evalCellFileWriteReason('Bun.write("src/app.ts", src)')).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
		expect(evalCellFileWriteReason("write('/tmp/../worktree/file', data)")).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
		expect(evalCellFileWriteReason('write(`/tmp/${target}`, data)')).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
		expect(evalCellFileWriteReason("Path('/tmp/../cli.rs').write_text(src)")).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
		expect(evalCellFileWriteReason("open('/tmp/../cli.rs', 'w')")).toBe(
			EVAL_FILE_WRITE_BLOCK_REASON,
		);
	});
});

describe("evalNoFileWrites", () => {
	test("blocks eval write cells and ignores other tools", async () => {
		const handlers: Array<(event: { toolName: string; input?: { code?: string } }) => Promise<unknown>> =
			[];
		evalNoFileWrites({
			on: (_event: string, handler: (event: { toolName: string; input?: { code?: string } }) => Promise<unknown>) => {
				handlers.push(handler);
			},
		} as never);

		expect(handlers).toHaveLength(1);
		expect(await handlers[0]!({ toolName: "edit", input: { code: "p.write_text('x')" } })).toBeUndefined();
		expect(await handlers[0]!({ toolName: "eval", input: { code: "print(1)" } })).toBeUndefined();
		expect(await handlers[0]!({ toolName: "eval", input: { code: "p.write_text(src)" } })).toEqual({
			block: true,
			reason: EVAL_FILE_WRITE_BLOCK_REASON,
		});
	});
});
