import { afterAll, beforeAll, describe, expect, it } from "bun:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createContinuationTransaction } from "../src/core/continuation";
import {
	CONTINUATION_MESSAGE_CUSTOM_TYPE,
	CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
	CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
	CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE,
	CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
	continuationMessageDetailsFor,
	createContinuationRequestWire,
	createContinuationSafetyReadyWire,
} from "../src/core/continuation-protocol";
import piVcc, { PI_VCC_LOAD_MARKER } from "../index";
import { createContinuationCoordinator } from "../src/core/coordinator";

let previousLogPath: string | undefined;
let logDir = "";

beforeAll(async () => {
	previousLogPath = process.env.PI_VCC_LOG_PATH;
	logDir = await mkdtemp(join(tmpdir(), "pi-vcc-coordinator-test-"));
	process.env.PI_VCC_LOG_PATH = join(logDir, "pi-vcc.jsonl");
});

afterAll(async () => {
	if (previousLogPath === undefined) delete process.env.PI_VCC_LOG_PATH;
	else process.env.PI_VCC_LOG_PATH = previousLogPath;
	await rm(logDir, { recursive: true, force: true });
});

const setup = (
	authority: "coordinator" = "coordinator",
	options: {
		sendFailures?: number;
		entries?: any[];
		clock?: number;
	} = {},
) => {
	const handlers: Record<string, Array<(event: any, ctx: any) => any>> = {};
	const wakeHandlers = new Set<(data: unknown) => void>();
	const entries = options.entries ?? [];
	const sent: any[] = [];
	const sendAttempts: any[] = [];
	const notifications: any[] = [];
	let remainingSendFailures = options.sendFailures ?? 0;
	let clock = options.clock ?? 100;
	const timers: Array<{
		callback: () => void;
		delay: number;
		cancelled: boolean;
	}> = [];
	const ctx = {
		sessionManager: { getBranch: () => entries },
		ui: {
			notify: (message: string, level: string) =>
				notifications.push({ message, level }),
		},
	} as any;
	const pi = {
		on: (event: string, handler: any) => {
			const eventHandlers = handlers[event] ?? [];
			eventHandlers.push(handler);
			handlers[event] = eventHandlers;
		},
		appendEntry: (customType: string, data: any) =>
			entries.push({
				id: `entry-${entries.length + 1}`,
				type: "custom",
				customType,
				data,
			}),
		sendMessage: (message: any, messageOptions: any) => {
			sendAttempts.push({ message, options: messageOptions });
			if (remainingSendFailures > 0) {
				remainingSendFailures -= 1;
				throw new Error("synchronous send failure");
			}
			sent.push({ message, options: messageOptions });
		},
		events: {
			on: (_channel: string, handler: any) => {
				wakeHandlers.add(handler);
				return () => wakeHandlers.delete(handler);
			},
			emit: (_channel: string, data: unknown) => {
				for (const handler of wakeHandlers) handler(data);
			},
		},
	} as any;
	const coordinator = createContinuationCoordinator(pi, {
		authority,
		now: () => clock,
		setTimer: (callback, delay) => {
			const timer = { callback, delay, cancelled: false };
			timers.push(timer);
			return timer as any;
		},
		clearTimer: (timer: any) => {
			timer.cancelled = true;
		},
		retryDelayMs: 5,
	});
	const emit = (event: string, payload: any = {}) => {
		for (const handler of handlers[event] ?? [])
			handler({ type: event, ...payload }, ctx);
	};
	const advance = (value: number) => {
		clock = value;
	};
	const fireTimer = (delay: number) => {
		const timer = timers.find(
			(candidate) => !candidate.cancelled && candidate.delay === delay,
		);
		if (!timer) throw new Error(`No active timer with delay ${delay}`);
		timer.cancelled = true;
		timer.callback();
	};
	return {
		coordinator,
		handlers,
		wakeHandlers,
		entries,
		sent,
		sendAttempts,
		notifications,
		timers,
		ctx,
		emit,
		advance,
		fireTimer,
		pi,
	};
};

const request = (
	h: ReturnType<typeof setup>,
	overrides: Record<string, unknown> = {},
) =>
	h.coordinator.request(
		{
			initiator: "compact_context",
			outcome: "compacted",
			attemptId: "attempt-1",
			requestId: "request-1",
			originatingRequestId: "request-1",
			resumePolicy: "active",
			deadlineMs: 100,
			retryLimit: 1,
			transactionId: "tx-1",
			...overrides,
		},
		h.ctx,
	);

const settleCurrent = (h: ReturnType<typeof setup>) => {
	const snapshot = h.coordinator.getPending();
	if (!snapshot) throw new Error("No pending transaction");
	h.emit("message_start", {
		message: {
			role: "custom",
			customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
			details: continuationMessageDetailsFor(snapshot),
		},
	});
	h.emit("message_end", { message: { role: "assistant", stopReason: "stop" } });
	h.emit("agent_settled");
};

describe("continuation coordinator", () => {
	it("registers one listener callback across both wake channels and persists request before submission", () => {
		const h = setup();
		request(h);
		expect(h.wakeHandlers.size).toBe(1);
		expect(h.entries[0].customType).toBe(
			CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
		);
		expect(h.sent).toHaveLength(1);
		expect(h.sent[0].options).toEqual({
			triggerTurn: true,
			deliverAs: "steer",
		});
		expect(h.sent[0].options.deliverAs).not.toBe("nextTurn");
	});

	it("durably queues every concurrent package request and processes them in request order", () => {
		const h = setup();
		const first = request(h);
		const second = request(h, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});

		expect(first.transactionId).toBe("tx-1");
		expect(second.transactionId).toBe("tx-2");
		expect(
			h.entries.filter(
				(entry) => entry.customType === CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
			),
		).toHaveLength(2);
		expect(h.sent.map((entry) => entry.message.details.transactionId)).toEqual([
			"tx-1",
		]);

		settleCurrent(h);
		expect(h.coordinator.getPending()?.transactionId).toBe("tx-2");
		expect(h.sent.map((entry) => entry.message.details.transactionId)).toEqual([
			"tx-1",
			"tx-2",
		]);

		settleCurrent(h);
		expect(h.coordinator.getPending()?.state).toBe("settled");
		const outcomes = h.entries.filter(
			(entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
		);
		expect(outcomes.map((entry) => entry.data.transactionId)).toEqual([
			"tx-1",
			"tx-2",
		]);
	});

	it("rebuilds queued activation grace from persisted request order after reload", () => {
		const beforeReload = setup();
		request(beforeReload, { deadlineMs: 1_000 });
		const queued = request(beforeReload, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
			deadlineMs: 100,
		});
		expect(queued.createdAt).toBe(100);
		expect(queued.deadlineAt).toBe(200);
		beforeReload.coordinator.dispose();

		const reloaded = setup("coordinator", {
			entries: beforeReload.entries,
			clock: 250,
		});
		reloaded.emit("session_start", { reason: "reload" });
		expect(reloaded.coordinator.getPending()?.transactionId).toBe("tx-1");

		settleCurrent(reloaded);

		const activated = reloaded.coordinator.getPending();
		expect(activated?.transactionId).toBe("tx-2");
		expect(activated?.createdAt).toBe(100);
		expect(activated?.deadlineAt).toBe(350);
		expect(activated?.state).toBe("submitted");
		expect(reloaded.sent.at(-1)?.message.details.transactionId).toBe("tx-2");
		expect(
			reloaded.entries.some(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === "tx-2" &&
					entry.data.snapshot.createdAt === 100 &&
					entry.data.snapshot.deadlineAt === 350,
			),
		).toBe(true);

		reloaded.advance(350);
		reloaded.fireTimer(100);
		expect(reloaded.coordinator.getPending()?.state).toBe("failed_loudly");
	});

	it("rejects removed runtime legacy authority atomically", () => {
		const previous = process.env.PI_VCC_CONTINUATION_AUTHORITY;
		const previousMarker = (globalThis as any)[PI_VCC_LOAD_MARKER];
		delete (globalThis as any)[PI_VCC_LOAD_MARKER];
		process.env.PI_VCC_CONTINUATION_AUTHORITY = "legacy";
		let registrations = 0;
		try {
			expect(() =>
				piVcc({
					events: { on: () => () => {} },
					on: () => {
						registrations += 1;
					},
				} as any),
			).toThrow("unsupported");
			expect((globalThis as any)[PI_VCC_LOAD_MARKER]).toBeUndefined();
			expect(registrations).toBe(0);
		} finally {
			if (previous === undefined)
				delete process.env.PI_VCC_CONTINUATION_AUTHORITY;
			else process.env.PI_VCC_CONTINUATION_AUTHORITY = previous;
			if (previousMarker === undefined)
				delete (globalThis as any)[PI_VCC_LOAD_MARKER];
			else (globalThis as any)[PI_VCC_LOAD_MARKER] = previousMarker;
		}
	});

	it("requires matching consumption, progress, then settlement", () => {
		const h = setup();
		request(h);
		settleCurrent(h);
		expect(h.entries.at(-1).customType).toBe(
			CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
		);
		expect(h.entries.at(-1).data.terminalState).toBe("settled");
	});

	it("reload keeps progressed active past its deadline until settlement", () => {
		const beforeReload = setup();
		const first = request(beforeReload, { deadlineMs: 100 });
		request(beforeReload, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});
		beforeReload.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(
					beforeReload.coordinator.getPending()!,
				),
			},
		});
		beforeReload.emit("message_end", {
			message: { role: "assistant", stopReason: "stop" },
		});
		expect(beforeReload.coordinator.getPending()?.state).toBe("progressed");
		beforeReload.coordinator.dispose();

		const reloaded = setup("coordinator", {
			entries: beforeReload.entries,
			clock: 250,
		});
		reloaded.emit("session_start", { reason: "reload" });
		expect(reloaded.coordinator.getPending()?.transactionId).toBe("tx-1");
		expect(reloaded.coordinator.getPending()?.state).toBe("progressed");
		expect(reloaded.notifications).toHaveLength(0);
		expect(reloaded.sent).toHaveLength(0);
		expect(
			reloaded.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
			),
		).toHaveLength(0);
		expect(reloaded.timers.every((timer) => timer.cancelled)).toBe(true);

		reloaded.emit("agent_settled");
		expect(reloaded.coordinator.getPending()?.transactionId).toBe("tx-2");
		expect(reloaded.coordinator.getPending()?.state).toBe("submitted");
		expect(reloaded.sent).toHaveLength(1);
		expect(reloaded.sent[0].message.details.transactionId).toBe("tx-2");
		const firstOutcome = reloaded.entries.find(
			(entry) =>
				entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
				entry.data.transactionId === "tx-1",
		);
		expect(firstOutcome?.data.terminalState).toBe("settled");
	});

	it.each([
		"error",
		"aborted",
	])("retries terminal assistant %s after consumption", (stopReason) => {
		const h = setup();
		const snapshot = request(h);
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		h.emit("message_end", { message: { role: "assistant", stopReason } });
		h.emit("agent_settled");
		expect(h.sent).toHaveLength(1);
		expect(h.coordinator.getPending()?.retryCount).toBe(1);
		h.fireTimer(5);
		expect(h.sent).toHaveLength(2);
	});

	it("a retry timer resubmits instead of synthesizing deadline expiry", () => {
		const h = setup("coordinator", { sendFailures: 1 });
		request(h, { retryLimit: 2 });
		expect(h.sendAttempts).toHaveLength(1);
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		expect(h.notifications).toHaveLength(0);

		h.fireTimer(5);
		expect(h.sendAttempts).toHaveLength(2);
		expect(h.sent).toHaveLength(1);
		expect(h.coordinator.getPending()?.state).toBe("submitted");
		expect(h.notifications).toHaveLength(0);
	});

	it("bounds repeated synchronous send throws and fails loudly", () => {
		const h = setup("coordinator", { sendFailures: 10 });
		request(h, { retryLimit: 1 });
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		h.fireTimer(5);
		expect(h.coordinator.getPending()?.state).toBe("failed_loudly");
		expect(h.coordinator.getPending()?.terminalReason).toBe(
			"retry_limit_exhausted",
		);
		expect(h.notifications.at(-1)?.message).toContain("Manual action");
	});

	it("settlement without consumption remains lifecycle-driven", () => {
		const h = setup();
		request(h);
		h.emit("agent_settled");
		expect(h.sent).toHaveLength(1);
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		h.fireTimer(5);
		expect(h.sent).toHaveLength(2);
	});

	it("does not release tool safety for unrelated tool completions, but matching persisted safety does", () => {
		const h = setup();
		const snapshot = request(h, { pendingToolCount: 2 });
		expect(h.sent).toHaveLength(0);

		h.emit("tool_execution_end", {
			toolCallId: "unrelated-secret-id",
			toolName: "read",
		});
		expect(h.coordinator.getPending()?.pendingToolCount).toBe(2);
		expect(h.sent).toHaveLength(0);

		h.entries.push({
			id: "unrelated-safety",
			type: "custom",
			customType: CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE,
			data: createContinuationSafetyReadyWire({
				transactionId: "other-tx",
				attemptId: snapshot.attemptId,
				requestId: snapshot.requestId,
			}),
		});
		h.pi.events.emit("pi-vcc:continuation-safety-ready", {
			transactionId: "other-tx",
		});
		expect(h.sent).toHaveLength(0);

		h.entries.push({
			id: "matching-safety",
			type: "custom",
			customType: CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE,
			data: createContinuationSafetyReadyWire({
				transactionId: snapshot.transactionId,
				attemptId: snapshot.attemptId,
				requestId: snapshot.requestId,
			}),
		});
		h.pi.events.emit("pi-vcc:continuation-safety-ready", {
			transactionId: snapshot.transactionId,
		});
		expect(h.coordinator.getPending()?.pendingToolCount).toBe(0);
		expect(h.sent).toHaveLength(1);
	});

	it("toolUse assistant message_end does not release tool safety", () => {
		const h = setup();
		request(h, { pendingToolCount: 1 });
		h.emit("message_end", { message: { role: "assistant", stopReason: "toolUse" } });
		expect(h.coordinator.getPending()?.state).toBe("waiting_tools");
		expect(h.coordinator.getPending()?.pendingToolCount).toBe(1);
		expect(h.sent).toHaveLength(0);
	});

	it("a lifecycle-safe completed assistant boundary releases tool safety", () => {
		const h = setup();
		request(h, { pendingToolCount: 1 });
		h.emit("message_end", {
			message: { role: "assistant", stopReason: "stop" },
		});
		expect(h.coordinator.getPending()?.state).toBe("submitted");
		expect(h.sent).toHaveLength(1);
	});

	it("deadline includes pending tool wait and warns with sanitized lifecycle diagnostics", () => {
		const h = setup();
		h.emit("agent_start");
		h.emit("turn_start");
		request(h, { pendingToolCount: 3 });
		expect(h.sent).toHaveLength(0);
		h.advance(200);
		h.fireTimer(100);
		expect(h.coordinator.getPending()?.state).toBe("failed_loudly");
		const warning = h.notifications.at(-1)?.message ?? "";
		expect(warning).toContain("pending-tools=3");
		expect(warning).toContain("last-state=waiting_tools");
		expect(warning).toContain(
			"epochs=session:0,input:0,agent:1,turn:1,message:0,settlement:0",
		);
		expect(warning).not.toContain("tool-id-secret");
	});

	it("real user and independent input supersede before matching consumption", () => {
		const realUser = setup();
		request(realUser);
		realUser.emit("input", { source: "interactive", text: "continue" });
		realUser.emit("message_start", {
			message: { role: "user", content: "continue" },
		});
		expect(
			realUser.entries.find(
				(entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
			)?.data.terminalReason,
		).toBe("real_user_input");

		const independent = setup();
		request(independent);
		independent.emit("message_start", {
			message: { role: "custom", customType: "goal-extension", details: {} },
		});
		expect(
			independent.entries.find(
				(entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
			)?.data.terminalReason,
		).toBe("independent_input");
	});

	it("lost/duplicate wakes reconcile branch authority without duplicate submissions", () => {
		const h = setup();
		request(h);
		h.pi.events.emit("pi-vcc:continuation-requested", { untrusted: true });
		h.pi.events.emit("pi-vcc:continuation-requested", {
			transactionId: "wrong",
		});
		expect(h.sent).toHaveLength(1);
	});

	it("reload rehydrates all pending work in order and restores exactly one listener", () => {
		const h = setup();
		request(h);
		request(h, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});
		h.emit("session_shutdown", { reason: "reload" });
		expect(h.wakeHandlers.size).toBe(0);

		h.emit("session_start", { reason: "reload" });
		expect(h.wakeHandlers.size).toBe(1);
		expect(h.coordinator.getPending()?.transactionId).toBe("tx-1");
		h.emit("session_start", { reason: "reload" });
		expect(h.wakeHandlers.size).toBe(1);
	});

	it.each([
		"new",
		"resume",
		"fork",
	])("terminalizes every pending old-session request before %s and restores one listener", (reason) => {
		const h = setup();
		request(h);
		request(h, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});
		h.emit("session_shutdown", { reason });
		expect(h.wakeHandlers.size).toBe(0);
		const outcomes = h.entries.filter(
			(entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
		);
		expect(outcomes.map((entry) => entry.data.transactionId)).toEqual([
			"tx-1",
			"tx-2",
		]);
		expect(
			outcomes.every(
				(entry) => entry.data.terminalReason === "session_replaced",
			),
		).toBe(true);

		const sentBefore = h.sent.length;
		for (const timer of h.timers) timer.callback();
		expect(h.sent).toHaveLength(sentBefore);

		const replacementEntries: any[] = [];
		h.ctx.sessionManager.getBranch = () => replacementEntries;
		h.emit("session_start", { reason });
		expect(h.wakeHandlers.size).toBe(1);
		expect(h.coordinator.getPending()).toBeUndefined();
	});

	it("merges persisted producer epochs with live epochs instead of regressing them", () => {
		const h = setup();
		h.emit("agent_start");
		h.emit("agent_start");
		const producer = createContinuationTransaction({
			transactionId: "producer-terminal",
			origin: "package-command",
			reason: "compacted",
			attemptId: "producer-attempt",
			resumePolicy: "terminal",
			createdAt: 100,
			deadlineMs: 100,
			epochs: {
				session: 0,
				input: 0,
				agent: 0,
				turn: 0,
				message: 0,
				settlement: 0,
			},
		});
		h.entries.push({
			id: "producer-request",
			type: "custom",
			customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
			data: createContinuationRequestWire(producer),
		});
		h.coordinator.reconcile(h.ctx);
		const outcome = h.entries.find(
			(entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
		);
		expect(outcome.data.snapshot.epochs.agent).toBe(2);

		const next = request(h, {
			transactionId: "tx-next",
			attemptId: "attempt-next",
		});
		expect(next.epochs.agent).toBe(2);
	});

	it("reconciles a standalone terminal-policy request into the sole coordinator-owned outcome", () => {
		const h = setup();
		const created = createContinuationTransaction({
			transactionId: "terminal-publisher",
			origin: "package-command",
			reason: "no-safe-cut",
			attemptId: "compact-now-1",
			resumePolicy: "terminal",
			createdAt: 100,
			deadlineMs: 0,
		});
		h.entries.push({
			id: "request",
			type: "custom",
			customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
			data: createContinuationRequestWire(created),
		});
		h.coordinator.reconcile(h.ctx);
		const outcomes = h.entries.filter(
			(entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
		);
		expect(outcomes).toHaveLength(1);
		expect(outcomes[0].data.terminalState).toBe("superseded");
		expect(outcomes[0].data.terminalReason).toBe("explicitly_stopped");
		expect(h.sent).toHaveLength(0);
	});
});
