import { beforeAll, describe, expect, mock, test } from "bun:test";

class MockText {
	constructor(
		public text: string,
		public paddingX = 0,
		public paddingY = 0,
	) {}

	render(): string[] {
		return [this.text];
	}

	invalidate(): void {}
}

mock.module("@mariozechner/pi-ai", () => ({
	StringEnum: (values: string[]) => ({ values }),
}));

mock.module("@mariozechner/pi-tui", () => ({
	matchesKey: () => false,
	Text: MockText,
	truncateToWidth: (text: string) => text,
}));

mock.module("@sinclair/typebox", () => ({
	Type: {
		Array: (items: unknown, options?: unknown) => ({ items, options }),
		Number: (options?: unknown) => ({ type: "number", options }),
		Object: (properties: unknown) => ({ properties }),
		Optional: (value: unknown) => value,
		String: (options?: unknown) => ({ type: "string", options }),
	},
}));

type RegisteredTool = {
	execute: (...args: any[]) => Promise<any>;
	renderResult: (...args: any[]) => MockText;
};

let todoExtension: typeof import("../_pi/extensions/todo").default;
let isTodoDetails: typeof import("../_pi/extensions/todo").isTodoDetails;

beforeAll(async () => {
	({ default: todoExtension, isTodoDetails } = await import("../_pi/extensions/todo"));
});

const setup = () => {
	const handlers: Record<string, (...args: any[]) => any> = {};
	let tool: RegisteredTool | undefined;

	todoExtension({
		on: (event: string, handler: (...args: any[]) => any) => {
			handlers[event] = handler;
		},
		registerTool: (definition: RegisteredTool) => {
			tool = definition;
		},
		registerCommand: () => {},
	} as any);

	if (!tool) throw new Error("todo tool was not registered");
	return { handlers, tool };
};

const theme = {
	fg: (_color: string, text: string) => text,
	bold: (text: string) => text,
};

describe("todo extension malformed session handling", () => {
	test("rejects empty and incomplete detail objects", () => {
		expect(isTodoDetails({})).toBe(false);
		expect(isTodoDetails({ action: "list", todos: [] })).toBe(false);
	});

	test("renderResult returns a component for empty details", () => {
		const { tool } = setup();
		const component = tool.renderResult(
			{ content: [{ type: "text", text: "Invalid tool arguments" }], details: {} },
			{ expanded: false, isPartial: false },
			theme,
			{},
		);

		expect(component).toBeInstanceOf(MockText);
		expect(component.render()).toEqual(["Invalid tool arguments"]);
	});

	test("state reconstruction ignores malformed trailing details", async () => {
		const { handlers, tool } = setup();
		await handlers.session_start?.(
			{},
			{
				sessionManager: {
					getBranch: () => [
						{
							type: "message",
							message: {
								role: "toolResult",
								toolName: "todo",
								details: {
									action: "add",
									todos: [{ id: 1, text: "Preserved", done: false }],
									nextId: 2,
								},
							},
						},
						{
							type: "message",
							message: { role: "toolResult", toolName: "todo", details: {} },
						},
					],
				},
			},
		);

		const result = await tool.execute("call-1", { action: "list" }, undefined, undefined, {});
		expect(result.content[0].text).toBe("[ ] #1: Preserved");
	});
});
