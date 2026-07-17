import { afterAll, beforeAll, describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createContinuationTransaction, transitionContinuation } from "../src/core/continuation";
import {
	CONTINUATION_MESSAGE_CUSTOM_TYPE,
	CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
	CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
	CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE,
	CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
	continuationMessageDetailsFor,
	createContinuationRequestWire,
	createContinuationSafetyReadyWire,
	createContinuationSnapshotWire,
} from "../src/core/continuation-protocol";
import piVcc, { PI_VCC_LOAD_MARKER } from "../index";
import {
	continuationLivenessCheckpointOrigin,
	createContinuationCoordinator,
} from "../src/core/coordinator";

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
		retryDelaysMs?: readonly number[];
		acceptanceDeadlineMs?: number;
		idleProgressDeadlineMs?: number;
		toolStallDeadlineMs?: number;
		toolLivenessCheckpointMs?: number;
		isIdle?: boolean;
		appendFailureCustomType?: string;
		appendFailureMatchOrdinal?: number;
		onSessionReplacement?: (reason: "reload" | "new" | "resume" | "fork") => void;
	} = {},
) => {
	const handlers: Record<string, Array<(event: any, ctx: any) => any>> = {};
	const wakeHandlers = new Set<{ channel: string; handler: (data: unknown) => void }>();
	const entries = options.entries ?? [];
	const sent: any[] = [];
	const sendAttempts: any[] = [];
	const notifications: any[] = [];
	let remainingSendFailures = options.sendFailures ?? 0;
	let appendFailureMatches = 0;
	let idle = options.isIdle ?? false;
	let clock = options.clock ?? 100;
	const timers: Array<{
		callback: () => void;
		delay: number;
		cancelled: boolean;
	}> = [];
	const ctx = {
		isIdle: () => idle,
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
		appendEntry: (customType: string, data: any) => {
			if (customType === options.appendFailureCustomType) {
				appendFailureMatches += 1;
				if (appendFailureMatches === (options.appendFailureMatchOrdinal ?? 1)) throw new Error(`injected ${customType} persistence failure`);
			}
			entries.push({
				id: `entry-${entries.length + 1}`,
				type: "custom",
				customType,
				data,
			});
		},
		sendMessage: (message: any, messageOptions: any) => {
			sendAttempts.push({ message, options: messageOptions });
			if (remainingSendFailures > 0) {
				remainingSendFailures -= 1;
				throw new Error("synchronous send failure");
			}
			sent.push({ message, options: messageOptions });
		},
		events: {
			on: (channel: string, handler: (data: unknown) => void) => {
				const subscription = { channel, handler };
				wakeHandlers.add(subscription);
				return () => wakeHandlers.delete(subscription);
			},
			emit: (channel: string, data: unknown) => {
				for (const subscription of wakeHandlers) {
					if (subscription.channel === channel) subscription.handler(data);
				}
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
		retryDelaysMs: options.retryDelaysMs ?? [5, 5],
		acceptanceDeadlineMs: options.acceptanceDeadlineMs,
		idleProgressDeadlineMs: options.idleProgressDeadlineMs,
		toolStallDeadlineMs: options.toolStallDeadlineMs,
		toolLivenessCheckpointMs: options.toolLivenessCheckpointMs,
		onSessionReplacement: options.onSessionReplacement,
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
		setIdle: (value: boolean) => { idle = value; },
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

const acceptWithTool = (
	h: ReturnType<typeof setup>,
	toolCallId: string,
	overrides: Record<string, unknown> = {},
) => {
	const snapshot = request(h, overrides);
	h.emit("message_start", {
		message: {
			role: "custom",
			customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
			details: continuationMessageDetailsFor(snapshot),
		},
	});
	h.emit("message_end", {
		message: {
			role: "assistant",
			stopReason: "toolUse",
			content: [{ type: "toolCall", id: toolCallId, name: "bash" }],
		},
	});
	return snapshot;
};

const transactionLogRecords = (transactionId: string) => {
	try {
		return readFileSync(process.env.PI_VCC_LOG_PATH!, "utf8")
			.trim()
			.split("\n")
			.filter(Boolean)
			.map((line) => JSON.parse(line))
			.filter((record) => record.transactionId === transactionId);
	} catch {
		return [];
	}
};

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
	it("registers both wake-channel subscriptions and persists request before submission", () => {
		const h = setup();
		request(h);
		expect(h.wakeHandlers.size).toBe(2);
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
		expect(reloaded.coordinator.getPending()?.state).toBe("retrying");
		expect(reloaded.coordinator.getPending()?.nextRetryAt).toBe(355);
		reloaded.advance(355);
		reloaded.fireTimer(5);
		expect(reloaded.sent).toHaveLength(1);
		reloaded.emit("agent_settled");
		expect(reloaded.coordinator.getPending()?.state).toBe("retrying");
		reloaded.advance(360);
		reloaded.fireTimer(5);
		expect(reloaded.coordinator.getPending()?.acceptanceDeadlineAt).toBe(460);
	});

	it.each(["reload", "new", "resume", "fork"] as const)(
		"%s releases the old package lease and registers exactly one functional replacement set",
		(reason) => {
			const previousMarker = (globalThis as any)[PI_VCC_LOAD_MARKER];
			delete (globalThis as any)[PI_VCC_LOAD_MARKER];
			const makePi = () => {
				const handlers: Record<string, any[]> = {};
				const entries: any[] = [];
				const sent: any[] = [];
				let lifecycleRegistrations = 0;
				let commandRegistrations = 0;
				let toolRegistrations = 0;
				const pi = {
					on: (event: string, handler: any) => {
						lifecycleRegistrations += 1;
						(handlers[event] ??= []).push(handler);
					},
					appendEntry: (customType: string, data: any) => entries.push({ type: "custom", customType, data }),
					sendMessage: (message: any, options: any) => sent.push({ message, options }),
					registerCommand: () => { commandRegistrations += 1; },
					registerTool: () => { toolRegistrations += 1; },
					events: { on: () => () => {} },
				} as any;
				const ctx = {
					isIdle: () => true,
					sessionManager: { getBranch: () => entries },
					ui: { notify: () => {} },
				} as any;
				return { pi, ctx, handlers, entries, sent, counts: () => ({ lifecycleRegistrations, commandRegistrations, toolRegistrations }) };
			};
			try {
				const first = makePi();
				piVcc(first.pi);
				const firstOwner = (globalThis as any)[PI_VCC_LOAD_MARKER];
				const firstCounts = first.counts();
				expect(firstCounts.lifecycleRegistrations).toBeGreaterThan(0);
				expect(firstCounts.commandRegistrations).toBeGreaterThan(0);
				expect(firstCounts.toolRegistrations).toBeGreaterThan(0);
				if (reason !== "reload") {
					firstOwner.coordinator.request({
						initiator: "compact_context",
						outcome: "compacted",
						attemptId: `${reason}-attempt`,
						transactionId: `${reason}-old-work`,
					}, first.ctx);
				}
				for (const handler of first.handlers.session_shutdown ?? []) handler({ reason }, first.ctx);
				expect((globalThis as any)[PI_VCC_LOAD_MARKER]).toBeUndefined();
				if (reason !== "reload") {
					expect(first.entries.some((entry) =>
						entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
						entry.data.transactionId === `${reason}-old-work` &&
						entry.data.terminalReason === "session_replaced",
					)).toBe(true);
				}

				const replacement = makePi();
				piVcc(replacement.pi);
				const replacementOwner = (globalThis as any)[PI_VCC_LOAD_MARKER];
				expect(replacementOwner).not.toBe(firstOwner);
				expect(replacement.counts()).toEqual(firstCounts);
				replacementOwner.coordinator.request({
					initiator: "compact_context",
					outcome: "compacted",
					attemptId: `${reason}-replacement-attempt`,
					transactionId: `${reason}-replacement-work`,
				}, replacement.ctx);
				expect(replacement.sent).toHaveLength(1);
				expect(replacement.sent[0].message.details.transactionId).toBe(`${reason}-replacement-work`);
				piVcc(replacement.pi);
				expect(replacement.counts()).toEqual(firstCounts);
			} finally {
				(globalThis as any)[PI_VCC_LOAD_MARKER]?.coordinator?.dispose();
				if (previousMarker === undefined) delete (globalThis as any)[PI_VCC_LOAD_MARKER];
				else (globalThis as any)[PI_VCC_LOAD_MARKER] = previousMarker;
			}
		},
	);

	it.each(["new", "resume", "fork"] as const)(
		"%s releases lifecycle ownership even when replacement outcome persistence fails",
		(reason) => {
			const replacements: string[] = [];
			const h = setup("coordinator", {
				appendFailureCustomType: CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
				onSessionReplacement: (replacementReason) => replacements.push(replacementReason),
			});
			request(h);
			expect(h.timers.some((timer) => !timer.cancelled)).toBe(true);
			expect(h.wakeHandlers.size).toBe(2);

			expect(() => h.emit("session_shutdown", { reason })).toThrow("persistence failure");
			expect(replacements).toEqual([reason]);
			expect(h.wakeHandlers.size).toBe(0);
			expect(h.timers.every((timer) => timer.cancelled)).toBe(true);
			expect(h.notifications).toHaveLength(1);
			expect(h.notifications[0]?.message).toContain("could not durably terminalize");

			const entriesBeforeStaleEvents = h.entries.length;
			h.emit("session_start", { reason });
			h.emit("agent_settled");
			for (const timer of h.timers) timer.callback();
			expect(h.entries).toHaveLength(entriesBeforeStaleEvents);
			expect(replacements).toEqual([reason]);
		},
	);

	it("reports the exact queued transaction whose replacement terminalization persistence fails", () => {
		const replacements: string[] = [];
		const h = setup("coordinator", {
			appendFailureCustomType: CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
			appendFailureMatchOrdinal: 2,
			onSessionReplacement: (reason) => replacements.push(reason),
		});
		request(h);
		request(h, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});
		expect(h.wakeHandlers.size).toBe(2);
		expect(() => h.emit("session_shutdown", { reason: "new" })).toThrow("persistence failure");
		expect(replacements).toEqual(["new"]);
		expect(h.notifications).toHaveLength(1);
		expect(h.notifications[0]?.message).toContain("transaction=tx-2");
		expect(h.notifications[0]?.message).not.toContain("transaction=unknown");
		expect(h.wakeHandlers.size).toBe(0);
		expect(h.timers.every((timer) => timer.cancelled)).toBe(true);
	});

	it.each([
		["new", 1],
		["new", 2],
		["resume", 1],
		["resume", 2],
		["fork", 1],
		["fork", 2],
	] as const)(
		"%s outcome #%d persistence failure releases the package lease for exactly one replacement registration",
		(reason, failureOrdinal) => {
			const previousMarker = (globalThis as any)[PI_VCC_LOAD_MARKER];
			delete (globalThis as any)[PI_VCC_LOAD_MARKER];
			const makePi = (failOutcomeOrdinal?: number) => {
				const handlers: Record<string, any[]> = {};
				const entries: any[] = [];
				const wakeHandlers = new Set<{ channel: string; handler: (data: unknown) => void }>();
				let outcomeAppends = 0;
				let registrations = 0;
				const pi = {
					on: (event: string, handler: any) => { registrations += 1; (handlers[event] ??= []).push(handler); },
					appendEntry: (customType: string, data: any) => {
						if (customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE) {
							outcomeAppends += 1;
							if (outcomeAppends === failOutcomeOrdinal) throw new Error("injected replacement outcome failure");
						}
						entries.push({ id: `entry-${entries.length + 1}`, type: "custom", customType, data });
					},
					sendMessage: () => {},
					registerCommand: () => { registrations += 1; },
					registerTool: () => { registrations += 1; },
					events: {
						on: (channel: string, handler: (data: unknown) => void) => {
							const subscription = { channel, handler };
							wakeHandlers.add(subscription);
							return () => wakeHandlers.delete(subscription);
						},
					},
				} as any;
				const ctx = {
					isIdle: () => true,
					sessionManager: { getBranch: () => entries },
					ui: { notify: () => {} },
				} as any;
				return { pi, ctx, handlers, entries, wakeHandlers, registrations: () => registrations };
			};
			try {
				const first = makePi(failureOrdinal);
				piVcc(first.pi);
				const firstOwner = (globalThis as any)[PI_VCC_LOAD_MARKER];
				firstOwner.coordinator.request({
					initiator: "compact_context",
					outcome: "compacted",
					attemptId: `${reason}-failure-attempt-1`,
					transactionId: `${reason}-failure-tx-1`,
				}, first.ctx);
				if (failureOrdinal === 2) {
					firstOwner.coordinator.request({
						initiator: "compact_context",
						outcome: "compacted",
						attemptId: `${reason}-failure-attempt-2`,
						transactionId: `${reason}-failure-tx-2`,
					}, first.ctx);
				}
				expect(first.wakeHandlers.size).toBe(2);
				expect(() => {
					for (const handler of first.handlers.session_shutdown ?? []) handler({ reason }, first.ctx);
				}).toThrow("replacement outcome failure");
				expect((globalThis as any)[PI_VCC_LOAD_MARKER]).toBeUndefined();
				expect(first.wakeHandlers.size).toBe(0);

				const replacement = makePi();
				piVcc(replacement.pi);
				const replacementRegistrations = replacement.registrations();
				expect(replacementRegistrations).toBeGreaterThan(0);
				piVcc(replacement.pi);
				expect(replacement.registrations()).toBe(replacementRegistrations);
				expect((globalThis as any)[PI_VCC_LOAD_MARKER]).not.toBe(firstOwner);
			} finally {
				(globalThis as any)[PI_VCC_LOAD_MARKER]?.coordinator?.dispose();
				if (previousMarker === undefined) delete (globalThis as any)[PI_VCC_LOAD_MARKER];
				else (globalThis as any)[PI_VCC_LOAD_MARKER] = previousMarker;
			}
		},
	);

	it("double package load acquires one process-wide lease before registering handlers", () => {
		const previousMarker = (globalThis as any)[PI_VCC_LOAD_MARKER];
		delete (globalThis as any)[PI_VCC_LOAD_MARKER];
		let lifecycleRegistrations = 0;
		let commandRegistrations = 0;
		let toolRegistrations = 0;
		const pi = {
			on: () => {
				lifecycleRegistrations += 1;
			},
			registerCommand: () => {
				commandRegistrations += 1;
			},
			registerTool: () => {
				toolRegistrations += 1;
			},
			events: { on: () => () => {} },
		} as any;
		try {
			piVcc(pi);
			const firstCounts = {
				lifecycleRegistrations,
				commandRegistrations,
				toolRegistrations,
			};
			piVcc(pi);
			expect({ lifecycleRegistrations, commandRegistrations, toolRegistrations }).toEqual(firstCounts);
			expect((globalThis as any)[PI_VCC_LOAD_MARKER]).toMatchObject({
				protocol: "pi-vcc-continuation",
				version: 2,
				status: "active",
			});
		} finally {
			(globalThis as any)[PI_VCC_LOAD_MARKER]?.coordinator?.dispose();
			if (previousMarker === undefined) delete (globalThis as any)[PI_VCC_LOAD_MARKER];
			else (globalThis as any)[PI_VCC_LOAD_MARKER] = previousMarker;
		}
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
		const activeProgressTimers = reloaded.timers.filter((timer) => !timer.cancelled);
		expect(activeProgressTimers).toHaveLength(1);
		expect(activeProgressTimers[0]?.delay).toBe(59_850);

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

	it.each(["settled", "failed_loudly", "superseded"] as const)(
		"reload completes a missing %s outcome once and activates the queued follower",
		(terminalState) => {
			const base = createContinuationTransaction({
				transactionId: "terminal-gap-tx",
				origin: "compact_context",
				reason: "compacted",
				attemptId: "terminal-gap-attempt",
				requestId: "terminal-gap-request",
				resumePolicy: "active",
				createdAt: 100,
				deadlineMs: 100,
			});
			let terminal = base;
			if (terminalState === "settled") {
				const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
				const accepted = transitionContinuation(submitted, {
					type: "durable_acceptance",
					at: 120,
					details: continuationMessageDetailsFor(submitted),
				}).snapshot;
				const progressed = transitionContinuation(accepted, {
					type: "assistant_result",
					at: 130,
					result: "progress",
					pendingToolCount: 0,
				}).snapshot;
				terminal = transitionContinuation(progressed, { type: "agent_settled", at: 140 }).snapshot;
			} else if (terminalState === "failed_loudly") {
				terminal = transitionContinuation(base, { type: "fail", at: 110, reason: "unrecoverable_error" }).snapshot;
			} else {
				terminal = transitionContinuation(base, { type: "supersede", at: 110, reason: "real_user_input" }).snapshot;
			}
			const follower = createContinuationTransaction({
				transactionId: "terminal-gap-follower",
				origin: "compact_context",
				reason: "compacted",
				attemptId: "terminal-gap-follower-attempt",
				requestId: "terminal-gap-follower-request",
				resumePolicy: "active",
				createdAt: 101,
				deadlineMs: 100,
			});
			const entries: any[] = [
				{ id: "terminal-gap-request-entry", type: "custom", customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, data: createContinuationRequestWire(base) },
				{ id: "terminal-gap-snapshot-entry", type: "custom", customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, data: createContinuationSnapshotWire(terminal) },
				{ id: "terminal-gap-follower-entry", type: "custom", customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, data: createContinuationRequestWire(follower) },
			];
			const h = setup("coordinator", { entries, clock: 200 });
			h.emit("session_start", { reason: "reload" });
			expect(entries.filter((entry) =>
				entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
				entry.data.transactionId === "terminal-gap-tx"
			)).toHaveLength(1);
			expect(h.coordinator.getPending()).toMatchObject({
				transactionId: "terminal-gap-follower",
				state: "submitted",
			});
			expect(h.sent).toHaveLength(1);

			h.emit("session_start", { reason: "reload" });
			h.coordinator.reconcile(h.ctx);
			expect(entries.filter((entry) =>
				entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
				entry.data.transactionId === "terminal-gap-tx"
			)).toHaveLength(1);
			expect(h.sent).toHaveLength(1);
		},
	);

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

	it.each(["error", "aborted"])(
		"does not reconsume persisted acceptance from failed %s ordinal before retry success",
		(stopReason) => {
			const h = setup();
			request(h);
			const firstDetails = h.sent[0].message.details;
			h.entries.push({
				id: `persisted-${stopReason}-ordinal-1`,
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: firstDetails,
				timestamp: 101,
			});
			h.advance(101);
			h.emit("message_end", { message: { role: "assistant", stopReason } });
			h.emit("agent_settled");
			expect(h.coordinator.getPending()).toMatchObject({
				state: "retrying",
				retryCount: 1,
				submissionCount: 1,
				acceptedAt: undefined,
			});

			h.advance(106);
			h.fireTimer(5);
			expect(h.sent).toHaveLength(2);
			expect(h.sent[1].message.details.submissionCount).toBe(2);
			expect(h.coordinator.getPending()).toMatchObject({
				state: "submitted",
				submissionCount: 2,
				acceptedAt: undefined,
			});

			h.entries.push({
				id: `persisted-${stopReason}-ordinal-2`,
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: h.sent[1].message.details,
				timestamp: 107,
			});
			h.advance(107);
			h.emit("message_end", {
				message: { role: "assistant", stopReason: "stop" },
			});
			h.emit("agent_settled");
			expect(h.coordinator.getPending()).toMatchObject({
				state: "settled",
				submissionCount: 2,
				terminalReason: "progressed_then_agent_settled",
			});
			expect(
				h.entries.filter(
					(entry) =>
						entry.type === "custom_message" &&
						entry.details?.transactionId === "tx-1",
				),
			).toHaveLength(2);
		},
	);

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

	it("pending tool safety wait does not consume the activated acceptance budget", () => {
		const h = setup();
		request(h, { pendingToolCount: 3 });
		expect(h.sent).toHaveLength(0);
		expect(h.timers.filter((timer) => !timer.cancelled)).toHaveLength(0);

		h.advance(5_000);
		h.emit("message_end", {
			message: { role: "assistant", stopReason: "stop" },
		});
		expect(h.coordinator.getPending()?.state).toBe("submitted");
		expect(h.coordinator.getPending()?.submittedAt).toBe(5_000);
		expect(h.coordinator.getPending()?.acceptanceDeadlineAt).toBe(5_100);
		expect(h.sent).toHaveLength(1);
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

	it("reload releases listeners while preserving pending work for the replacement coordinator", () => {
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
		expect(h.wakeHandlers.size).toBe(0);
		expect(h.coordinator.getPending()?.transactionId).toBe("tx-1");
		h.emit("session_start", { reason: "reload" });
		expect(h.wakeHandlers.size).toBe(0);
	});

	it.each([
		"new",
		"resume",
		"fork",
	])("terminalizes every pending old-session request before %s and leaves the old coordinator disposed", (reason) => {
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
		expect(h.wakeHandlers.size).toBe(0);
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

	it("accepts a persisted top-level custom_message without message_start", () => {
		const h = setup("coordinator", { idleProgressDeadlineMs: 60 });
		const snapshot = request(h);
		const acceptanceTimer = h.timers.find((timer) => !timer.cancelled);
		h.advance(125);
		h.entries.push({
			id: "durable-continuation",
			type: "custom_message",
			customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
			details: continuationMessageDetailsFor(snapshot),
			timestamp: 125,
		});
		h.coordinator.reconcile(h.ctx);
		expect(h.coordinator.getPending()?.state).toBe("consumed");
		expect(h.coordinator.getPending()?.acceptedAt).toBe(125);
		expect(acceptanceTimer?.cancelled).toBe(true);
		expect(h.timers.some((timer) => !timer.cancelled && timer.delay === 60)).toBe(true);
	});

	it("reconciles no-message_start acceptance before assistant progress and settles exactly once", () => {
		const h = setup("coordinator", { idleProgressDeadlineMs: 60, retryDelaysMs: [1_000, 2_000] });
		const submitted = request(h);
		h.entries.push({
			id: "host-persisted-without-message-start",
			type: "custom_message",
			customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
			details: continuationMessageDetailsFor(submitted),
			timestamp: 101,
		});
		h.advance(102);
		h.emit("message_end", { message: { role: "assistant", stopReason: "stop" } });
		expect(h.coordinator.getPending()?.state).toBe("progressed");
		expect(h.coordinator.getPending()?.acceptedAt).toBe(101);
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.state).toBe("settled");
		h.emit("agent_settled");
		expect(h.entries.filter((entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE)).toHaveLength(1);
		expect(h.sent).toHaveLength(1);
	});

	it("folds persistence after custom message_end but before agent_settled without resending a streaming steer", () => {
		const h = setup("coordinator", { idleProgressDeadlineMs: 60, retryDelaysMs: [1_000, 2_000] });
		const submitted = request(h);
		h.emit("message_end", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(submitted),
			},
		});
		h.entries.push({
			id: "host-persisted-after-message-end",
			type: "custom_message",
			customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
			details: continuationMessageDetailsFor(submitted),
			timestamp: 101,
		});
		h.advance(102);
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		expect(h.coordinator.getPending()?.retryCount).toBe(1);
		expect(h.sent).toHaveLength(1);
	});

	it("does not fold failed-ordinal durable acceptance during retry backoff", () => {
		const h = setup("coordinator", { retryDelaysMs: [1_000, 2_000] });
		const submitted = request(h);
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		h.entries.push({
			id: "late-failed-ordinal-acceptance",
			type: "custom_message",
			customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
			details: continuationMessageDetailsFor(submitted),
			timestamp: 150,
		});
		h.advance(1_100);
		h.fireTimer(1_000);
		expect(h.coordinator.getPending()).toMatchObject({
			state: "submitted",
			submissionCount: 2,
			acceptedAt: undefined,
		});
		expect(h.sent).toHaveLength(2);
	});

	it("ignores unrelated assistant and tool activity before durable acceptance", () => {
		const h = setup();
		request(h);
		const before = h.coordinator.getPending();
		h.emit("message_end", {
			message: {
				role: "assistant",
				stopReason: "toolUse",
				content: [{ type: "toolCall", id: "private-id", name: "read" }],
			},
		});
		h.emit("tool_execution_start", { toolCallId: "private-id" });
		h.emit("tool_execution_end", { toolCallId: "private-id" });
		const after = h.coordinator.getPending();
		expect(after?.state).toBe("submitted");
		expect(after?.acceptedAt).toBeUndefined();
		expect(after?.lastProgressAt).toBeUndefined();
		expect(after?.acceptanceDeadlineAt).toBe(before?.acceptanceDeadlineAt);
	});

	it.each([4_726, 5_246])("gives queued work a full 100ms activation budget after %dms of queue wait", (queueWait) => {
		const h = setup();
		request(h, { deadlineMs: queueWait + 1_000 });
		request(h, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
			deadlineMs: 100,
		});
		h.advance(100 + queueWait);
		settleCurrent(h);
		const queued = h.coordinator.getPending();
		expect(queued?.transactionId).toBe("tx-2");
		expect(queued?.submittedAt).toBe(100 + queueWait);
		expect(queued?.acceptanceDeadlineAt).toBe(200 + queueWait);
	});

	it.each(["error", "aborted"])("paces %s after partial progress through the first 1s retry", (stopReason) => {
		const h = setup("coordinator", { retryDelaysMs: [1_000, 2_000] });
		const snapshot = request(h, { retryLimit: 2, deadlineMs: 15_000 });
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		h.emit("message_end", { message: { role: "assistant", stopReason: "stop" } });
		h.emit("message_end", { message: { role: "assistant", stopReason } });
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		expect(h.coordinator.getPending()?.retryCount).toBe(1);
		expect(h.sent).toHaveLength(1);
		h.fireTimer(1_000);
		expect(h.sent).toHaveLength(2);
	});

	it("uses host idle readiness to resubmit an asynchronously rejected delivery without settlement", () => {
		const h = setup("coordinator", { retryDelaysMs: [1_000, 2_000], isIdle: true });
		request(h, { retryLimit: 2, deadlineMs: 10 });
		h.advance(110);
		h.fireTimer(10);
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		expect(h.sent).toHaveLength(1);

		h.advance(1_110);
		h.fireTimer(1_000);
		expect(h.sent).toHaveLength(2);
		expect(h.sent.map((entry) => entry.message.details.submissionCount)).toEqual([1, 2]);
	});

	it("preserves settlement gating while the host remains active", () => {
		const h = setup("coordinator", { retryDelaysMs: [1_000, 2_000], isIdle: false });
		request(h, { retryLimit: 2, deadlineMs: 10 });
		h.advance(110);
		h.fireTimer(10);
		h.advance(1_110);
		h.fireTimer(1_000);
		expect(h.sent).toHaveLength(1);
	});

	it("gates acceptance-expiry retries on settlement without double-counting duplicate settlement", () => {
		const h = setup("coordinator", { retryDelaysMs: [1_000, 2_000] });
		request(h, { retryLimit: 2, deadlineMs: 10 });
		h.advance(110);
		h.fireTimer(10);
		expect(h.coordinator.getPending()?.state).toBe("retrying");
		expect(h.coordinator.getPending()?.retryCount).toBe(1);
		expect(h.sent).toHaveLength(1);

		h.emit("agent_start");
		h.advance(500);
		h.emit("agent_settled");
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.retryCount).toBe(1);
		expect(h.sent).toHaveLength(1);
		h.advance(1_500);
		h.fireTimer(1_000);
		expect(h.sent).toHaveLength(2);

		h.advance(1_510);
		h.fireTimer(10);
		expect(h.coordinator.getPending()?.retryCount).toBe(2);
		h.advance(3_510);
		h.fireTimer(2_000);
		expect(h.sent).toHaveLength(2);
		h.advance(3_600);
		h.emit("agent_settled");
		expect(h.sent).toHaveLength(2);
		h.advance(5_600);
		h.fireTimer(2_000);
		expect(h.sent).toHaveLength(3);
		expect(h.sent.map((entry) => entry.message.details.submissionCount)).toEqual([1, 2, 3]);
	});

	it("paces two retries at exactly 1s then 2s after settlement", () => {
		const h = setup("coordinator", { retryDelaysMs: [1_000, 2_000] });
		request(h, { retryLimit: 2, deadlineMs: 15_000 });
		for (const [delay, stopReason] of [[1_000, "aborted"], [2_000, "error"]] as const) {
			const snapshot = h.coordinator.getPending()!;
			h.emit("message_start", {
				message: {
					role: "custom",
					customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
					details: continuationMessageDetailsFor(snapshot),
				},
			});
			h.emit("message_end", { message: { role: "assistant", stopReason } });
			h.emit("agent_settled");
			expect(h.coordinator.getPending()?.state).toBe("retrying");
			h.fireTimer(delay);
		}
		expect(h.sent).toHaveLength(3);
		expect(h.sent.map((entry) => entry.message.details.submissionCount)).toEqual([1, 2, 3]);
	});

	it("refreshes tool stall only for correlated tool_execution_update events and stalls after true silence", () => {
		const h = setup("coordinator", { toolStallDeadlineMs: 50, idleProgressDeadlineMs: 60 });
		const snapshot = request(h);
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		h.emit("message_end", {
			message: {
				role: "assistant",
				stopReason: "toolUse",
				content: [{ type: "toolCall", id: "long-tool", name: "bash" }],
			},
		});
		for (const at of [140, 180, 220]) {
			h.advance(at);
			h.emit("tool_execution_update", { toolCallId: "long-tool", toolName: "bash" });
			expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(at + 50);
		}
		h.advance(240);
		h.emit("tool_execution_update", { toolCallId: "other-tool", toolName: "bash" });
		expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(270);
		expect(h.coordinator.getPending()?.state).toBe("progressed");
		h.advance(270);
		h.fireTimer(50);
		expect(h.coordinator.getPending()?.state).toBe("stalled");
		expect(h.notifications).toHaveLength(1);
	});

	it("durably defers each active-host progress deadline and expires once the host becomes idle", () => {
		const transactionId = "active-deferral-boundaries";
		const h = setup("coordinator", {
			idleProgressDeadlineMs: 60,
			isIdle: false,
		});
		acceptWithTool(h, "active-deferral-tool", { transactionId });
		h.advance(110);
		h.emit("tool_execution_end", {
			toolCallId: "active-deferral-tool",
			toolName: "bash",
		});
		const before = h.coordinator.getPending()!;
		const snapshotCount = () =>
			h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === transactionId,
			).length;
		const snapshotsBefore = snapshotCount();
		const logsBefore = transactionLogRecords(transactionId).length;
		const firstDeadlineTimer = h.timers.find(
			(timer) => !timer.cancelled && timer.delay === 60,
		)!;

		h.advance(170);
		h.fireTimer(60);
		const firstDeferral = h.coordinator.getPending()!;
		expect(firstDeferral).toMatchObject({
			state: "progressed",
			lastProgressAt: before.lastProgressAt,
			pendingToolCount: before.pendingToolCount,
			lastAssistantResult: before.lastAssistantResult,
			progressDeadlineAt: 230,
			deadlineAt: 230,
			phaseEpoch: (before.phaseEpoch ?? 0) + 1,
		});
		expect(snapshotCount()).toBe(snapshotsBefore + 1);
		expect(transactionLogRecords(transactionId)).toHaveLength(logsBefore + 1);
		expect(h.notifications).toHaveLength(0);
		expect(
			h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
					entry.data.transactionId === transactionId,
			),
		).toHaveLength(0);

		const secondDeadlineTimer = h.timers.find(
			(timer) => !timer.cancelled && timer.delay === 60,
		)!;
		firstDeadlineTimer.callback();
		expect(secondDeadlineTimer.cancelled).toBe(false);
		expect(h.timers.filter((timer) => !timer.cancelled)).toEqual([
			secondDeadlineTimer,
		]);
		expect(snapshotCount()).toBe(snapshotsBefore + 1);

		h.advance(230);
		h.fireTimer(60);
		expect(h.coordinator.getPending()).toMatchObject({
			state: "progressed",
			progressDeadlineAt: 290,
			deadlineAt: 290,
			phaseEpoch: (before.phaseEpoch ?? 0) + 2,
		});
		expect(snapshotCount()).toBe(snapshotsBefore + 2);
		expect(transactionLogRecords(transactionId)).toHaveLength(logsBefore + 2);

		h.setIdle(true);
		h.advance(290);
		h.fireTimer(60);
		expect(h.coordinator.getPending()).toMatchObject({
			state: "failed_loudly",
			terminalReason: "deadline_expired",
		});
		expect(h.notifications).toHaveLength(1);
	});

	it("rehydrates future and past-due active deferrals without granting no-tool grace", () => {
		const transactionId = "active-deferral-reload";
		const beforeReload = setup("coordinator", {
			idleProgressDeadlineMs: 60,
			isIdle: false,
		});
		acceptWithTool(beforeReload, "deferral-reload-tool", { transactionId });
		beforeReload.advance(110);
		beforeReload.emit("tool_execution_end", {
			toolCallId: "deferral-reload-tool",
		});
		beforeReload.advance(170);
		beforeReload.fireTimer(60);
		expect(beforeReload.coordinator.getPending()?.progressDeadlineAt).toBe(230);
		const stalePreReloadTimer = beforeReload.timers.find(
			(timer) => !timer.cancelled && timer.delay === 60,
		)!;
		beforeReload.coordinator.dispose();
		const durableEntries = structuredClone(beforeReload.entries);

		const future = setup("coordinator", {
			entries: structuredClone(durableEntries),
			clock: 200,
			idleProgressDeadlineMs: 60,
			isIdle: false,
		});
		future.emit("session_start", { reason: "reload" });
		expect(future.coordinator.getPending()?.progressDeadlineAt).toBe(230);
		expect(
			future.timers.filter((timer) => !timer.cancelled).map((timer) => timer.delay),
		).toEqual([30]);
		const futureEntryCount = future.entries.length;
		stalePreReloadTimer.callback();
		expect(future.entries).toHaveLength(futureEntryCount);
		expect(future.coordinator.getPending()?.progressDeadlineAt).toBe(230);
		future.coordinator.dispose();

		const pastDueActive = setup("coordinator", {
			entries: structuredClone(durableEntries),
			clock: 250,
			idleProgressDeadlineMs: 60,
			isIdle: false,
		});
		pastDueActive.emit("session_start", { reason: "reload" });
		expect(
			pastDueActive.timers.filter((timer) => !timer.cancelled).map((timer) => timer.delay),
		).toEqual([0]);
		pastDueActive.fireTimer(0);
		expect(pastDueActive.coordinator.getPending()).toMatchObject({
			state: "progressed",
			progressDeadlineAt: 310,
			deadlineAt: 310,
		});
		pastDueActive.coordinator.dispose();

		const pastDueIdle = setup("coordinator", {
			entries: structuredClone(durableEntries),
			clock: 250,
			idleProgressDeadlineMs: 60,
			isIdle: true,
		});
		pastDueIdle.emit("session_start", { reason: "reload" });
		pastDueIdle.fireTimer(0);
		expect(pastDueIdle.coordinator.getPending()).toMatchObject({
			state: "failed_loudly",
			terminalReason: "deadline_expired",
		});
	});

	it("does not expire accepted progress while the host is still running the next model turn", () => {
		const h = setup("coordinator", {
			idleProgressDeadlineMs: 60,
			isIdle: false,
		});
		const snapshot = request(h);
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		h.emit("message_end", {
			message: {
				role: "assistant",
				stopReason: "toolUse",
				content: [{ type: "toolCall", id: "completed-tool", name: "bash" }],
			},
		});
		h.advance(110);
		h.emit("tool_execution_end", { toolCallId: "completed-tool", toolName: "bash" });
		expect(h.coordinator.getPending()).toMatchObject({
			state: "progressed",
			pendingToolCount: 0,
			progressDeadlineAt: 170,
		});

		// Reproduce the observed sessions: Pi starts the next model turn, but the
		// provider takes longer than 60 seconds to produce the next assistant
		// message. Active inference must retain continuation ownership.
		h.advance(160);
		h.emit("turn_start");
		h.advance(170);
		h.fireTimer(60);

		expect(h.coordinator.getPending()?.state).toBe("progressed");
		expect(h.notifications).toHaveLength(0);
		expect(
			h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
					entry.data.terminalState === "failed_loudly",
			),
		).toHaveLength(0);

		h.advance(176);
		h.emit("message_end", {
			message: { role: "assistant", stopReason: "stop" },
		});
		h.emit("agent_settled");
		expect(h.coordinator.getPending()).toMatchObject({
			state: "settled",
			terminalReason: "progressed_then_agent_settled",
		});
	});

	it("checkpoints correlated tool liveness without persisting every update", () => {
		const h = setup("coordinator", {
			toolStallDeadlineMs: 900_000,
			idleProgressDeadlineMs: 60_000,
		});
		const snapshot = request(h);
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		h.emit("message_end", {
			message: {
				role: "assistant",
				stopReason: "toolUse",
				content: [{ type: "toolCall", id: "streaming-tool", name: "bash" }],
			},
		});

		const snapshotCount = () =>
			h.entries.filter(
				(entry) => entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
			).length;
		const beforeUpdates = snapshotCount();

		// Production tools commonly emit updates every ~250ms. Deadline freshness
		// remains in memory, while durable liveness is checkpointed at a bounded
		// cadence instead of appending one session entry and log record per update.
		for (const at of [350, 600, 850, 1_100, 5_100, 10_100, 20_100, 30_099]) {
			h.advance(at);
			h.emit("tool_execution_update", {
				toolCallId: "streaming-tool",
				toolName: "bash",
			});
			expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(at + 900_000);
		}
		expect(snapshotCount()).toBe(beforeUpdates);

		h.advance(30_100);
		h.emit("tool_execution_update", {
			toolCallId: "streaming-tool",
			toolName: "bash",
		});
		expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(930_100);
		expect(snapshotCount()).toBe(beforeUpdates + 1);
	});

	it("stalls an outstanding tool, retains queue ownership, then resumes on correlated progress", () => {
		const h = setup("coordinator", { toolStallDeadlineMs: 50, idleProgressDeadlineMs: 60 });
		const snapshot = request(h);
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		h.emit("message_end", {
			message: {
				role: "assistant",
				stopReason: "toolUse",
				content: [{ type: "toolCall", id: "redacted", name: "read" }],
			},
		});
		request(h, {
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});
		h.advance(150);
		h.fireTimer(50);
		expect(h.coordinator.getPending()?.state).toBe("stalled");
		expect(h.coordinator.getPending()?.transactionId).toBe("tx-1");
		expect(h.sent).toHaveLength(1);
		expect(h.notifications).toHaveLength(1);
		expect(h.notifications[0]?.message).not.toContain("redacted");

		h.advance(160);
		h.emit("tool_execution_end", { toolCallId: "redacted" });
		expect(h.coordinator.getPending()?.state).toBe("progressed");
		expect(h.coordinator.getPending()?.pendingToolCount).toBe(0);
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.transactionId).toBe("tx-2");
		expect(h.sent).toHaveLength(2);
	});

	it("writes one matching snapshot and transaction log at each liveness checkpoint boundary", () => {
		const transactionId = "checkpoint-boundary-log";
		const h = setup("coordinator", {
			toolStallDeadlineMs: 900_000,
			toolLivenessCheckpointMs: 30_000,
		});
		acceptWithTool(h, "checkpoint-log-tool", { transactionId });
		const snapshotCount = () =>
			h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === transactionId,
			).length;
		const snapshotsBefore = snapshotCount();
		const logsBefore = transactionLogRecords(transactionId).length;

		h.advance(30_099);
		h.emit("tool_execution_update", {
			toolCallId: "checkpoint-log-tool",
		});
		expect(snapshotCount()).toBe(snapshotsBefore);
		expect(transactionLogRecords(transactionId)).toHaveLength(logsBefore);

		h.advance(30_100);
		h.emit("tool_execution_update", {
			toolCallId: "checkpoint-log-tool",
		});
		expect(snapshotCount()).toBe(snapshotsBefore + 1);
		expect(transactionLogRecords(transactionId)).toHaveLength(logsBefore + 1);

		h.advance(60_099);
		h.emit("tool_execution_update", {
			toolCallId: "checkpoint-log-tool",
		});
		expect(snapshotCount()).toBe(snapshotsBefore + 1);
		h.advance(60_100);
		h.emit("tool_execution_update", {
			toolCallId: "checkpoint-log-tool",
		});
		expect(snapshotCount()).toBe(snapshotsBefore + 2);
		expect(transactionLogRecords(transactionId)).toHaveLength(logsBefore + 2);
	});

	it("caps the effective checkpoint at half of a shorter tool-stall deadline", () => {
		const transactionId = "short-stall-checkpoint";
		const h = setup("coordinator", {
			toolStallDeadlineMs: 10,
			toolLivenessCheckpointMs: 100,
		});
		acceptWithTool(h, "short-stall-tool", { transactionId });
		const snapshotCount = () =>
			h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === transactionId,
			).length;
		const before = snapshotCount();
		h.advance(104);
		h.emit("tool_execution_update", { toolCallId: "short-stall-tool" });
		expect(snapshotCount()).toBe(before);
		h.advance(105);
		h.emit("tool_execution_update", { toolCallId: "short-stall-tool" });
		expect(snapshotCount()).toBe(before + 1);
		expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(115);
	});

	it("rejects unsupported checkpoint and tool-stall timing options", () => {
		for (const value of [0, 1, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY]) {
			expect(() => setup("coordinator", { toolStallDeadlineMs: value })).toThrow(
				"toolStallDeadlineMs",
			);
		}
		for (const value of [0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY]) {
			expect(() =>
				setup("coordinator", { toolLivenessCheckpointMs: value }),
			).toThrow("toolLivenessCheckpointMs");
		}
		expect(() =>
			setup("coordinator", {
				toolStallDeadlineMs: 2,
				toolLivenessCheckpointMs: 1,
			}),
		).not.toThrow();
	});

	it("uses lastProgressAt then acceptedAt then createdAt as the live coordinator checkpoint origin", () => {
		const base = createContinuationTransaction({
			transactionId: "checkpoint-origin",
			origin: "compact_context",
			reason: "compacted",
			attemptId: "checkpoint-origin-attempt",
			resumePolicy: "active",
			createdAt: 100,
			deadlineMs: 100,
		});
		expect(
			continuationLivenessCheckpointOrigin({
				...base,
				acceptedAt: 120,
				lastProgressAt: 130,
			}),
		).toBe(130);
		expect(
			continuationLivenessCheckpointOrigin({
				...base,
				acceptedAt: 120,
			}),
		).toBe(120);
		expect(continuationLivenessCheckpointOrigin(base)).toBe(100);

		const h = setup("coordinator", { toolLivenessCheckpointMs: 30 });
		const submitted = request(h, { transactionId: "checkpoint-origin-live" });
		expect(h.coordinator.getNextToolLivenessCheckpointAt()).toBe(130);
		h.advance(120);
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(submitted),
			},
		});
		expect(h.coordinator.getNextToolLivenessCheckpointAt()).toBe(150);
		h.advance(140);
		h.emit("message_end", {
			message: {
				role: "assistant",
				stopReason: "toolUse",
				content: [{ type: "toolCall", id: "checkpoint-origin-tool", name: "bash" }],
			},
		});
		expect(h.coordinator.getNextToolLivenessCheckpointAt()).toBe(170);
	});

	it("preserves uncheckpointed live liveness and its timer across reconcile and queued-request wakes", () => {
		const transactionId = "same-process-live-liveness";
		const h = setup("coordinator", {
			toolStallDeadlineMs: 50,
			toolLivenessCheckpointMs: 30_000,
		});
		acceptWithTool(h, "same-process-tool", { transactionId });
		const snapshotsBeforeUpdate = h.entries.filter(
			(entry) =>
				entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
				entry.data.snapshot.transactionId === transactionId,
		).length;
		h.advance(120);
		h.emit("tool_execution_update", { toolCallId: "same-process-tool" });
		const live = h.coordinator.getPending()!;
		const liveTimer = h.timers.find(
			(timer) => !timer.cancelled && timer.delay === 50,
		)!;
		expect(live.toolStallDeadlineAt).toBe(170);

		h.coordinator.reconcile(h.ctx);
		expect(h.coordinator.getPending()).toBe(live);
		expect(liveTimer.cancelled).toBe(false);
		expect(h.timers.filter((timer) => !timer.cancelled)).toEqual([liveTimer]);

		request(h, {
			transactionId: "same-process-queued",
			attemptId: "same-process-queued-attempt",
			requestId: "same-process-queued-request",
			originatingRequestId: "same-process-queued-request",
		});
		h.pi.events.emit("pi-vcc:continuation-requested", {
			transactionId: "same-process-queued",
		});
		expect(h.coordinator.getPending()).toBe(live);
		expect(h.coordinator.getPending()).toMatchObject({
			lastProgressAt: 120,
			toolStallDeadlineAt: 170,
			phaseEpoch: live.phaseEpoch,
		});
		expect(liveTimer.cancelled).toBe(false);
		expect(
			h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === transactionId,
			).length,
		).toBe(snapshotsBeforeUpdate);

		h.advance(170);
		h.fireTimer(50);
		expect(h.coordinator.getPending()).toMatchObject({
			transactionId,
			state: "stalled",
		});
	});

	it("grants restored active tools one fresh stall interval on every reload", () => {
		const transactionId = "active-tool-reload-grace";
		const beforeReload = setup("coordinator", {
			toolStallDeadlineMs: 50,
			toolLivenessCheckpointMs: 30_000,
		});
		const submitted = acceptWithTool(beforeReload, "reload-grace-tool", {
			transactionId,
		});
		beforeReload.entries.push(
			{
				id: "reload-grace-acceptance",
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(submitted),
				timestamp: 100,
			},
			{
				id: "reload-grace-tool-call",
				type: "message",
				message: {
					role: "assistant",
					stopReason: "toolUse",
					content: [
						{
							type: "toolCall",
							id: "reload-grace-tool",
							name: "bash",
						},
					],
				},
			},
		);
		beforeReload.advance(124);
		beforeReload.emit("tool_execution_update", {
			toolCallId: "reload-grace-tool",
		});
		expect(beforeReload.coordinator.getPending()?.toolStallDeadlineAt).toBe(174);
		const staleTimer = beforeReload.timers.find(
			(timer) => !timer.cancelled && timer.delay === 50,
		)!;
		const durableEntries = structuredClone(beforeReload.entries);
		const durableSnapshotCount = durableEntries.filter(
			(entry) =>
				entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
				entry.data.snapshot.transactionId === transactionId,
		).length;
		beforeReload.coordinator.dispose();

		const firstReload = setup("coordinator", {
			entries: structuredClone(durableEntries),
			clock: 149,
			toolStallDeadlineMs: 50,
			toolLivenessCheckpointMs: 30_000,
		});
		firstReload.emit("session_start", { reason: "reload" });
		expect(firstReload.coordinator.getPending()).toMatchObject({
			state: "progressed",
			toolStallDeadlineAt: 199,
			deadlineAt: 199,
		});
		expect(
			firstReload.timers.filter((timer) => !timer.cancelled).map((timer) => timer.delay),
		).toEqual([50]);
		expect(
			firstReload.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === transactionId,
			).length,
		).toBe(durableSnapshotCount);
		staleTimer.callback();
		expect(firstReload.coordinator.getPending()?.toolStallDeadlineAt).toBe(199);
		firstReload.coordinator.dispose();

		const secondReload = setup("coordinator", {
			entries: structuredClone(durableEntries),
			clock: 180,
			toolStallDeadlineMs: 50,
			toolLivenessCheckpointMs: 30_000,
		});
		secondReload.emit("session_start", { reason: "reload" });
		expect(secondReload.coordinator.getPending()?.toolStallDeadlineAt).toBe(230);
		secondReload.advance(229);
		expect(secondReload.coordinator.getPending()?.state).toBe("progressed");
		secondReload.advance(230);
		secondReload.fireTimer(50);
		expect(secondReload.coordinator.getPending()?.state).toBe("stalled");
	});

	it("flushes uncheckpointed liveness immediately on material completion, settlement, and supersession", () => {
		const completionId = "material-completion";
		const completion = setup("coordinator", {
			toolStallDeadlineMs: 100,
			toolLivenessCheckpointMs: 50,
		});
		acceptWithTool(completion, "material-completion-tool", {
			transactionId: completionId,
		});
		completion.advance(120);
		completion.emit("tool_execution_update", {
			toolCallId: "material-completion-tool",
		});
		const completionSnapshots = () =>
			completion.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === completionId,
			).length;
		const snapshotsBeforeCompletion = completionSnapshots();
		const logsBeforeCompletion = transactionLogRecords(completionId).length;
		completion.advance(121);
		completion.emit("tool_execution_end", {
			toolCallId: "material-completion-tool",
		});
		expect(completion.coordinator.getPending()).toMatchObject({
			pendingToolCount: 0,
			lastProgressAt: 121,
		});
		expect(completionSnapshots()).toBe(snapshotsBeforeCompletion + 1);
		expect(transactionLogRecords(completionId)).toHaveLength(
			logsBeforeCompletion + 1,
		);
		completion.emit("agent_settled");
		expect(completionSnapshots()).toBe(snapshotsBeforeCompletion + 2);
		expect(transactionLogRecords(completionId)).toHaveLength(
			logsBeforeCompletion + 2,
		);

		const supersessionId = "material-supersession";
		const supersession = setup("coordinator", {
			toolStallDeadlineMs: 100,
			toolLivenessCheckpointMs: 50,
		});
		acceptWithTool(supersession, "material-supersession-tool", {
			transactionId: supersessionId,
		});
		supersession.advance(120);
		supersession.emit("tool_execution_update", {
			toolCallId: "material-supersession-tool",
		});
		const snapshotsBeforeSupersession = supersession.entries.filter(
			(entry) =>
				entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
				entry.data.snapshot.transactionId === supersessionId,
		).length;
		supersession.advance(121);
		supersession.emit("input", {
			source: "interactive",
			text: "new work",
		});
		const persistedSupersession = supersession.entries.filter(
			(entry) =>
				entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
				entry.data.snapshot.transactionId === supersessionId,
		).at(-1)?.data.snapshot;
		expect(persistedSupersession).toMatchObject({
			state: "superseded",
			lastProgressAt: 120,
			toolStallDeadlineAt: undefined,
		});
		expect(
			supersession.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === supersessionId,
			).length,
		).toBe(snapshotsBeforeSupersession + 1);
	});

	it("persists immediate snapshot and log pairs for tool starts, assistant results, stalls, and retries", () => {
		const immediatePair = (
			transactionId: string,
			h: ReturnType<typeof setup>,
			action: () => void,
		) => {
			const snapshotsBefore = h.entries.filter(
				(entry) =>
					entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
					entry.data.snapshot.transactionId === transactionId,
			).length;
			const logsBefore = transactionLogRecords(transactionId).length;
			action();
			expect(
				h.entries.filter(
					(entry) =>
						entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
						entry.data.snapshot.transactionId === transactionId,
				).length,
			).toBe(snapshotsBefore + 1);
			expect(transactionLogRecords(transactionId)).toHaveLength(logsBefore + 1);
		};

		const toolStartId = "material-tool-start";
		const toolStart = setup("coordinator", {
			toolStallDeadlineMs: 100,
			toolLivenessCheckpointMs: 50,
		});
		acceptWithTool(toolStart, "material-tool-start-call", { transactionId: toolStartId });
		toolStart.advance(120);
		toolStart.emit("tool_execution_update", { toolCallId: "material-tool-start-call" });
		toolStart.advance(121);
		immediatePair(toolStartId, toolStart, () =>
			toolStart.emit("tool_execution_start", { toolCallId: "material-tool-start-call" }),
		);

		const assistantId = "material-assistant-result";
		const assistant = setup("coordinator", {
			toolStallDeadlineMs: 100,
			toolLivenessCheckpointMs: 50,
		});
		acceptWithTool(assistant, "material-assistant-call", { transactionId: assistantId });
		assistant.advance(120);
		assistant.emit("tool_execution_update", { toolCallId: "material-assistant-call" });
		assistant.advance(121);
		immediatePair(assistantId, assistant, () =>
			assistant.emit("message_end", {
				message: { role: "assistant", stopReason: "error" },
			}),
		);

		const stallId = "material-stall";
		const stall = setup("coordinator", {
			toolStallDeadlineMs: 100,
			toolLivenessCheckpointMs: 50,
		});
		acceptWithTool(stall, "material-stall-call", { transactionId: stallId });
		stall.advance(120);
		stall.emit("tool_execution_update", { toolCallId: "material-stall-call" });
		stall.advance(220);
		immediatePair(stallId, stall, () => stall.fireTimer(100));
		expect(stall.coordinator.getPending()?.state).toBe("stalled");

		const retryId = "material-retry";
		const retry = setup("coordinator", { retryDelaysMs: [5, 5] });
		const submitted = request(retry, { transactionId: retryId });
		retry.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(submitted),
			},
		});
		retry.emit("message_end", {
			message: { role: "assistant", stopReason: "error" },
		});
		immediatePair(retryId, retry, () => retry.emit("agent_settled"));
		expect(retry.coordinator.getPending()?.state).toBe("retrying");
	});

	it("keeps status-only messages neutral and supersedes model-driving or unknown custom input", () => {
		for (const message of [
			{ role: "custom", customType: "ad-process:update" },
			{ role: "custom", customType: "heartbeat", details: { piVccInputIntent: "status" } },
		]) {
			const h = setup();
			request(h);
			h.emit("message_start", { message });
			expect(h.coordinator.getPending()?.state).toBe("submitted");
		}
		for (const customType of ["vcc-recall", "claude-review-completion", "compaction-nudge", "unknown-model-input"]) {
			const h = setup();
			request(h);
			h.emit("message_start", { message: { role: "custom", customType } });
			expect(h.coordinator.getPending()?.state).toBe("superseded");
			expect(h.coordinator.getPending()?.terminalReason).toBe("independent_input");
		}
	});

	it("rehydrates version 1 active tools with a stall watchdog and restores representable correlation", () => {
		const base = createContinuationTransaction({
			transactionId: "legacy-tool-tx",
			origin: "compact_context",
			reason: "compacted",
			attemptId: "legacy-tool-attempt",
			requestId: "legacy-tool-request",
			resumePolicy: "active",
			createdAt: 100,
			deadlineMs: 60_000,
		});
		const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
		const accepted = transitionContinuation(submitted, {
			type: "durable_acceptance",
			at: 120,
			details: continuationMessageDetailsFor(submitted),
		}).snapshot;
		const progressed = transitionContinuation(accepted, {
			type: "assistant_result",
			at: 130,
			result: "progress",
			pendingToolCount: 1,
			toolStallDeadlineAt: 1_030,
		}).snapshot;
		const {
			queuedAt: _queuedAt,
			phaseEpoch: _phaseEpoch,
			submittedAt: _submittedAt,
			acceptanceDeadlineAt: _acceptanceDeadlineAt,
			progressDeadlineAt: _progressDeadlineAt,
			toolStallDeadlineAt: _toolStallDeadlineAt,
			...legacyFields
		} = progressed;
		const legacy = { ...legacyFields, version: 1 as const };
		const requestSnapshot = { ...legacy, state: "created" as const, submissionCount: 0, pendingToolCount: 0, acceptedAt: undefined, lastProgressAt: undefined, lastAssistantResult: undefined };
		const entries = [
			{
				id: "legacy-tool-request-entry",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 1, kind: "request", snapshot: requestSnapshot },
			},
			{
				id: "legacy-tool-acceptance",
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: { ...continuationMessageDetailsFor(submitted), version: 1 },
				timestamp: 120,
			},
			{
				id: "legacy-tool-snapshot-entry",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 1, kind: "snapshot", snapshot: legacy },
			},
			{
				id: "legacy-tool-call-message",
				type: "message",
				message: { role: "assistant", stopReason: "toolUse", content: [{ type: "toolCall", id: "legacy-tool-id", name: "bash" }] },
			},
		];
		const h = setup("coordinator", { entries, clock: 200, toolStallDeadlineMs: 50 });
		h.emit("session_start", { reason: "reload" });
		expect(h.coordinator.getPending()?.version).toBe(2);
		expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(250);
		expect(h.timers.some((timer) => !timer.cancelled && timer.delay === 50)).toBe(true);
		h.advance(250);
		h.fireTimer(50);
		expect(h.coordinator.getPending()?.state).toBe("stalled");
		h.advance(260);
		h.emit("tool_execution_update", { toolCallId: "legacy-tool-id" });
		expect(h.coordinator.getPending()?.state).toBe("progressed");
		expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(310);
	});

	it("rehydrates version 2 active-tool correlation and completes after matching stalled recovery", () => {
		const base = createContinuationTransaction({
			transactionId: "v2-tool-tx",
			origin: "compact_context",
			reason: "compacted",
			attemptId: "v2-tool-attempt",
			requestId: "v2-tool-request",
			resumePolicy: "active",
			createdAt: 100,
			deadlineMs: 60_000,
		});
		const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
		const accepted = transitionContinuation(submitted, {
			type: "durable_acceptance",
			at: 120,
			details: continuationMessageDetailsFor(submitted),
		}).snapshot;
		const progressed = transitionContinuation(accepted, {
			type: "assistant_result",
			at: 130,
			result: "progress",
			pendingToolCount: 1,
			toolStallDeadlineAt: 250,
		}).snapshot;
		const entries = [
			{
				id: "v2-tool-request-entry",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: createContinuationRequestWire(base, "compacted"),
			},
			{
				id: "v2-tool-acceptance",
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(submitted),
				timestamp: 120,
			},
			{
				id: "v2-tool-snapshot-entry",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 2, kind: "snapshot", snapshot: progressed },
			},
			{
				id: "v2-tool-call-message",
				type: "message",
				message: { role: "assistant", stopReason: "toolUse", content: [{ type: "toolCall", id: "v2-tool-id", name: "bash" }] },
			},
		];
		const h = setup("coordinator", { entries, clock: 200, toolStallDeadlineMs: 50, idleProgressDeadlineMs: 60 });
		h.emit("session_start", { reason: "reload" });
		expect(h.coordinator.getPending()?.state).toBe("progressed");
		expect(h.timers.filter((timer) => !timer.cancelled && timer.delay === 50)).toHaveLength(1);
		expect(h.sent).toHaveLength(0);

		h.advance(250);
		h.fireTimer(50);
		expect(h.coordinator.getPending()?.state).toBe("stalled");
		h.advance(260);
		h.emit("tool_execution_update", { toolCallId: "v2-tool-id" });
		expect(h.coordinator.getPending()?.state).toBe("progressed");
		expect(h.coordinator.getPending()?.toolStallDeadlineAt).toBe(310);
		h.emit("tool_execution_end", { toolCallId: "v2-tool-id" });
		expect(h.coordinator.getPending()?.pendingToolCount).toBe(0);
		h.emit("agent_settled");
		expect(h.coordinator.getPending()?.state).toBe("settled");
		expect(h.sent).toHaveLength(0);
		expect(entries.filter((entry) => entry.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE)).toHaveLength(1);
		expect(entries.filter((entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE)).toHaveLength(1);
	});

	it.each([1, 2] as const)(
		"rehydrates version %i partial parallel-tool batches and settles the remaining tool exactly once",
		(version) => {
			const base = createContinuationTransaction({
				transactionId: `v${version}-parallel-tool-tx`,
				origin: "compact_context",
				reason: "compacted",
				attemptId: `v${version}-parallel-tool-attempt`,
				requestId: `v${version}-parallel-tool-request`,
				resumePolicy: "active",
				createdAt: 100,
				deadlineMs: 60_000,
			});
			const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
			const accepted = transitionContinuation(submitted, {
				type: "durable_acceptance",
				at: 120,
				details: continuationMessageDetailsFor(submitted),
			}).snapshot;
			const parallel = transitionContinuation(accepted, {
				type: "assistant_result",
				at: 130,
				result: "progress",
				pendingToolCount: 2,
				toolStallDeadlineAt: 250,
			}).snapshot;
			const partiallyCompleted = transitionContinuation(parallel, {
				type: "tool_progress",
				at: 140,
				pendingToolCount: 1,
				toolStallDeadlineAt: 250,
			}).snapshot;
			const toVersion = (snapshot: typeof partiallyCompleted) => {
				if (version === 2) return snapshot;
				const {
					queuedAt: _queuedAt,
					phaseEpoch: _phaseEpoch,
					submittedAt: _submittedAt,
					acceptanceDeadlineAt: _acceptanceDeadlineAt,
					progressDeadlineAt: _progressDeadlineAt,
					toolStallDeadlineAt: _toolStallDeadlineAt,
					nextRetryAt: _nextRetryAt,
					activatedAt: _activatedAt,
					...legacy
				} = snapshot;
				return { ...legacy, version: 1 as const };
			};
			const requestSnapshot = toVersion({
				...base,
				state: "created",
				pendingToolCount: 0,
				submissionCount: 0,
			});
			const persisted = toVersion(partiallyCompleted);
			const entries = [
				{
					id: `v${version}-parallel-request-entry`,
					type: "custom",
					customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
					data: { protocol: "pi-vcc-continuation", version, kind: "request", snapshot: requestSnapshot },
				},
				{
					id: `v${version}-parallel-acceptance`,
					type: "custom_message",
					customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
					details: { ...continuationMessageDetailsFor(submitted), version },
					timestamp: 120,
				},
				{
					id: `v${version}-parallel-snapshot-entry`,
					type: "custom",
					customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
					data: { protocol: "pi-vcc-continuation", version, kind: "snapshot", snapshot: persisted },
				},
				{
					id: `v${version}-parallel-assistant-message`,
					type: "message",
					message: {
						role: "assistant",
						stopReason: "toolUse",
						content: [
							{ type: "toolCall", id: `v${version}-completed-tool`, name: "read" },
							{ type: "toolCall", id: `v${version}-remaining-tool`, name: "bash" },
						],
					},
				},
			];
			entries.push(
				{
					id: `v${version}-parallel-independent-input`,
					type: "custom_message",
					customType: "vcc-recall",
					details: {},
				},
				{
					id: `v${version}-parallel-post-boundary-assistant`,
					type: "message",
					message: {
						role: "assistant",
						stopReason: "toolUse",
						content: [{ type: "toolCall", id: `v${version}-post-boundary-tool`, name: "bash" }],
					},
				},
			);
			const h = setup("coordinator", { entries, clock: 200, toolStallDeadlineMs: 50 });
			h.emit("session_start", { reason: "reload" });
			expect(h.coordinator.getPending()?.pendingToolCount).toBe(1);

			// The persisted count proves that one call finished, but Pi has not yet
			// persisted either result. An unrelated ID remains non-authoritative;
			// the matching update disambiguates the still-running call.
			h.emit("tool_execution_update", { toolCallId: "unrelated-tool" });
			h.emit("tool_execution_end", { toolCallId: `v${version}-post-boundary-tool` });
			expect(h.coordinator.getPending()?.lastProgressAt).toBe(140);
			expect(h.coordinator.getPending()?.pendingToolCount).toBe(1);
			h.advance(210);
			h.emit("tool_execution_update", { toolCallId: `v${version}-remaining-tool` });
			expect(h.coordinator.getPending()?.lastProgressAt).toBe(210);
			h.advance(220);
			h.emit("tool_execution_end", { toolCallId: `v${version}-remaining-tool` });
			expect(h.coordinator.getPending()?.pendingToolCount).toBe(0);
			h.emit("agent_settled");
			expect(h.coordinator.getPending()?.state).toBe("settled");
			expect(entries.filter((entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE)).toHaveLength(1);
			h.emit("tool_execution_end", { toolCallId: `v${version}-completed-tool` });
			h.emit("agent_settled");
			expect(entries.filter((entry) => entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE)).toHaveLength(1);
		},
	);

	it("rehydrates version 1 retrying work after folding durable acceptance before scheduling resubmission", () => {
		const base = createContinuationTransaction({
			transactionId: "legacy-retrying-tx",
			origin: "compact_context",
			reason: "compacted",
			attemptId: "legacy-retrying-attempt",
			requestId: "legacy-retrying-request",
			resumePolicy: "active",
			createdAt: 100,
			deadlineMs: 60_000,
		});
		const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
		const retrying = transitionContinuation(submitted, {
			type: "acceptance_deadline",
			at: submitted.acceptanceDeadlineAt!,
			nextRetryAt: submitted.acceptanceDeadlineAt! + 1_000,
		}).snapshot;
		const { queuedAt: _queuedAt, phaseEpoch: _phaseEpoch, submittedAt: _submittedAt, acceptanceDeadlineAt: _acceptanceDeadlineAt, nextRetryAt: _nextRetryAt, ...legacyFields } = retrying;
		const legacy = { ...legacyFields, version: 1 as const };
		const {
			queuedAt: _submittedQueuedAt,
			phaseEpoch: _submittedPhaseEpoch,
			submittedAt: _submittedTimestamp,
			acceptanceDeadlineAt: _submittedAcceptanceDeadline,
			...legacySubmittedFields
		} = submitted;
		const legacySubmitted = { ...legacySubmittedFields, version: 1 as const };
		const entries = [
			{
				id: "legacy-retrying-request-entry",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: {
					protocol: "pi-vcc-continuation",
					version: 1,
					kind: "request",
					snapshot: { ...legacy, state: "created", submissionCount: 0, retryCount: 0 },
				},
			},
			{
				id: "legacy-retrying-submitted-entry",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 1, kind: "snapshot", snapshot: legacySubmitted },
			},
			{
				id: "legacy-retrying-snapshot-entry",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 1, kind: "snapshot", snapshot: legacy },
			},
			{
				id: "legacy-retrying-durable-message",
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: { ...continuationMessageDetailsFor(submitted), version: 1 },
				timestamp: 120,
			},
		];
		const h = setup("coordinator", { entries, clock: 200, idleProgressDeadlineMs: 60 });
		h.emit("session_start", { reason: "reload" });
		expect(h.coordinator.getPending()?.version).toBe(2);
		expect(h.coordinator.getPending()?.state).toBe("consumed");
		expect(h.coordinator.getPending()?.acceptedAt).toBe(120);
		expect(h.sent).toHaveLength(0);
		expect(h.coordinator.getPending()?.nextRetryAt).toBeUndefined();
	});

	it("fails closed when version 1 retrying persistence cannot explain a matching durable ordinal", () => {
		const base = createContinuationTransaction({
			transactionId: "legacy-ambiguous-retry-tx",
			origin: "compact_context",
			reason: "compacted",
			attemptId: "legacy-ambiguous-retry-attempt",
			requestId: "legacy-ambiguous-retry-request",
			resumePolicy: "active",
			createdAt: 100,
			deadlineMs: 100,
		});
		const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
		const retrying = transitionContinuation(submitted, {
			type: "acceptance_deadline",
			at: submitted.acceptanceDeadlineAt!,
			nextRetryAt: 215,
		}).snapshot;
		const toLegacy = (snapshot: typeof base) => {
			const legacy = { ...snapshot } as any;
			for (const key of ["queuedAt", "phaseEpoch", "submittedAt", "acceptanceDeadlineAt", "progressDeadlineAt", "toolStallDeadlineAt", "nextRetryAt"]) delete legacy[key];
			legacy.version = 1;
			return legacy;
		};
		const entries = [
			{
				id: "legacy-ambiguous-request-entry",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 1, kind: "request", snapshot: toLegacy(base) },
			},
			{
				id: "legacy-ambiguous-retrying-entry",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: { protocol: "pi-vcc-continuation", version: 1, kind: "snapshot", snapshot: toLegacy(retrying) },
			},
			{
				id: "legacy-ambiguous-durable-message",
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: { ...continuationMessageDetailsFor(submitted), version: 1 },
				timestamp: 120,
			},
		];
		const h = setup("coordinator", { entries, clock: 200, retryDelaysMs: [5, 5] });
		h.emit("session_start", { reason: "reload" });
		expect(h.coordinator.getPending()).toMatchObject({ state: "retrying", acceptedAt: undefined });
		h.fireTimer(5);
		expect(h.sent).toHaveLength(1);
		expect(h.sent[0].message.details.submissionCount).toBe(2);
	});

	it.each(["error", "aborted"] as const)(
		"rehydrates version 1 accepted %s retry persistence without reconsuming the failed ordinal",
		(stopReason) => {
			const base = createContinuationTransaction({
				transactionId: `legacy-${stopReason}-retry-tx`,
				origin: "compact_context",
				reason: "compacted",
				attemptId: `legacy-${stopReason}-retry-attempt`,
				requestId: `legacy-${stopReason}-retry-request`,
				resumePolicy: "active",
				createdAt: 100,
				deadlineMs: 100,
			});
			const submitted = transitionContinuation(base, { type: "submitted", at: 110 }).snapshot;
			const accepted = transitionContinuation(submitted, {
				type: "durable_acceptance",
				at: 120,
				details: continuationMessageDetailsFor(submitted),
			}).snapshot;
			const failed = transitionContinuation(accepted, {
				type: "assistant_result",
				at: 130,
				result: stopReason,
			}).snapshot;
			const retrying = transitionContinuation(failed, {
				type: "agent_settled",
				at: 140,
				nextRetryAt: 145,
			}).snapshot;
			const toLegacy = (snapshot: typeof base) => {
				const legacy = { ...snapshot } as any;
				for (const key of ["queuedAt", "phaseEpoch", "submittedAt", "acceptanceDeadlineAt", "progressDeadlineAt", "toolStallDeadlineAt", "nextRetryAt"]) delete legacy[key];
				legacy.version = 1;
				return legacy;
			};
			const entries = [
				{
					id: `legacy-${stopReason}-request-entry`,
					type: "custom",
					customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
					data: { protocol: "pi-vcc-continuation", version: 1, kind: "request", snapshot: toLegacy(base) },
				},
				...[
					submitted,
					accepted,
					failed,
					retrying,
				].map((snapshot, index) => ({
					id: `legacy-${stopReason}-snapshot-${index}`,
					type: "custom",
					customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
					data: { protocol: "pi-vcc-continuation", version: 1, kind: "snapshot", snapshot: toLegacy(snapshot) },
				})),
				{
					id: `legacy-${stopReason}-durable-message`,
					type: "custom_message",
					customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
					details: { ...continuationMessageDetailsFor(submitted), version: 1 },
					timestamp: 120,
				},
			];
			const h = setup("coordinator", { entries, clock: 200, retryDelaysMs: [5, 5] });
			h.emit("session_start", { reason: "reload" });
			expect(h.coordinator.getPending()).toMatchObject({
				version: 2,
				state: "retrying",
				submissionCount: 1,
				acceptedAt: undefined,
			});
			expect(h.sent).toHaveLength(0);
			h.fireTimer(5);
			expect(h.sent).toHaveLength(1);
			expect(h.sent[0].message.details.submissionCount).toBe(2);
		},
	);

	it("rehydrates version 1 submitted work after folding durable acceptance before timers or sends", () => {
		const base = createContinuationTransaction({
			transactionId: "legacy-tx",
			origin: "compact_context",
			reason: "compacted",
			attemptId: "legacy-attempt",
			requestId: "legacy-request",
			resumePolicy: "active",
			createdAt: 100,
			deadlineMs: 60_000,
		});
		const submitted = transitionContinuation(base, {
			type: "submitted",
			at: 110,
		}).snapshot;
		const { queuedAt: _queuedAt, phaseEpoch: _phaseEpoch, submittedAt: _submittedAt, acceptanceDeadlineAt: _acceptanceDeadlineAt, ...legacyFields } = submitted;
		const legacy = { ...legacyFields, version: 1 as const };
		const entries = [
			{
				id: "legacy-request-entry",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: {
					protocol: "pi-vcc-continuation",
					version: 1,
					kind: "request",
					snapshot: { ...legacy, state: "created", submissionCount: 0 },
				},
			},
			{
				id: "legacy-snapshot-entry",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: {
					protocol: "pi-vcc-continuation",
					version: 1,
					kind: "snapshot",
					snapshot: legacy,
				},
			},
			{
				id: "legacy-durable-message",
				type: "custom_message",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: { ...continuationMessageDetailsFor(submitted), version: 1 },
				timestamp: 120,
			},
		];
		const h = setup("coordinator", { entries, clock: 200, idleProgressDeadlineMs: 60 });
		h.emit("session_start", { reason: "reload" });
		expect(h.coordinator.getPending()?.version).toBe(2);
		expect(h.coordinator.getPending()?.state).toBe("consumed");
		expect(h.coordinator.getPending()?.acceptedAt).toBe(120);
		expect(h.sent).toHaveLength(0);
		const adaptedIndex = h.entries.findIndex((entry) =>
			entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
			entry.data.snapshot.version === 2 &&
			entry.data.snapshot.transactionId === "legacy-tx"
		);
		expect(adaptedIndex).toBeGreaterThan(2);
		expect(h.timers.some((timer) => !timer.cancelled)).toBe(true);
	});

	it("ignores cancelled or stale phase timers after durable acceptance", () => {
		const h = setup("coordinator", { idleProgressDeadlineMs: 60 });
		const snapshot = request(h);
		const staleTimer = h.timers.find((timer) => !timer.cancelled)!;
		h.emit("message_start", {
			message: {
				role: "custom",
				customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
				details: continuationMessageDetailsFor(snapshot),
			},
		});
		expect(staleTimer.cancelled).toBe(true);
		staleTimer.callback();
		expect(h.coordinator.getPending()?.state).toBe("consumed");
		expect(h.notifications).toHaveLength(0);
	});
});
