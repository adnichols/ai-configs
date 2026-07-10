import { describe, expect, it } from "bun:test";
import {
	type ContinuationEvent,
	createContinuationTransaction,
	isContinuationTerminal,
	transitionContinuation,
} from "../src/core/continuation";
import {
	adaptContinuationInitiatorOutcome,
	CONTINUATION_ATTEMPT_OUTCOMES,
	CONTINUATION_INITIATORS,
	CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
	CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
	CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
	CONTINUATION_TERMINAL_STATES,
	type ContinuationTransactionSnapshot,
	continuationMessageDetailsFor,
	createContinuationOutcomeWire,
	createContinuationRequestWire,
	createContinuationSafetyReadyWire,
	createContinuationSnapshotWire,
	parseContinuationOutcome,
	parseContinuationRequest,
	parseContinuationSafetyReady,
	parseContinuationSnapshot,
	reconcileContinuationEntries,
	serializeContinuationWire,
} from "../src/core/continuation-protocol";

const created = (
	overrides: Partial<Parameters<typeof createContinuationTransaction>[0]> = {},
) =>
	createContinuationTransaction({
		transactionId: "tx-1",
		origin: "compact_context",
		reason: "compacted",
		compactionId: "compact-1",
		attemptId: "attempt-1",
		requestId: "request-1",
		originatingRequestId: "request-1",
		resumePolicy: "active",
		createdAt: 100,
		deadlineMs: 1_000,
		retryLimit: 2,
		epochs: { session: 1 },
		...overrides,
	});

const matchingMessage = (snapshot: ContinuationTransactionSnapshot) => ({
	role: "custom",
	customType: "pi-vcc-continuation",
	details: continuationMessageDetailsFor(snapshot),
});

const step = (
	snapshot: ContinuationTransactionSnapshot,
	event: ContinuationEvent,
) => transitionContinuation(snapshot, event).snapshot;

const progressed = (snapshot = created()) => {
	const submitted = step(snapshot, {
		type: "submitted",
		at: 120,
		epochs: { message: 1 },
	});
	const consumed = step(submitted, {
		type: "message_start",
		at: 130,
		message: matchingMessage(submitted),
		epochs: { message: 2 },
	});
	return step(consumed, {
		type: "assistant_result",
		at: 150,
		result: "progress",
		epochs: { message: 3 },
	});
};

describe("continuation state machine", () => {
	it("follows the legal created/waiting/submitted/consumed/progressed/settled path", () => {
		let snapshot = created({ pendingToolCount: 2 });
		expect(snapshot.state).toBe("created");
		expect(snapshot.deadlineAt).toBe(1_100);

		snapshot = step(snapshot, {
			type: "tools_pending",
			at: 110,
			pendingToolCount: 2,
		});
		expect(snapshot.state).toBe("waiting_tools");

		const toolsReady = transitionContinuation(snapshot, {
			type: "tools_ready",
			at: 115,
		});
		expect(toolsReady.decision).toBe("submit");
		snapshot = toolsReady.snapshot;

		snapshot = step(snapshot, {
			type: "submitted",
			at: 120,
			epochs: { message: 1 },
		});
		expect(snapshot.state).toBe("submitted");
		expect(snapshot.submissionCount).toBe(1);

		snapshot = step(snapshot, {
			type: "message_start",
			at: 130,
			message: matchingMessage(snapshot),
			epochs: { message: 2 },
		});
		expect(snapshot.state).toBe("consumed");
		expect(snapshot.consumedEpochs?.message).toBe(2);

		snapshot = step(snapshot, {
			type: "assistant_result",
			at: 150,
			result: "progress",
			epochs: { message: 3 },
		});
		expect(snapshot.state).toBe("progressed");

		const settled = transitionContinuation(snapshot, {
			type: "agent_settled",
			at: 160,
			epochs: { settlement: 1 },
		});
		expect(settled.decision).toBe("settled");
		expect(settled.snapshot.state).toBe("settled");
		expect(isContinuationTerminal(settled.snapshot)).toBe(true);
	});

	it("is idempotent for duplicate matching lifecycle events", () => {
		const submitted = step(created(), {
			type: "submitted",
			at: 120,
			epochs: { message: 1 },
		});
		expect(
			transitionContinuation(submitted, {
				type: "submitted",
				at: 121,
				epochs: { message: 1 },
			}).disposition,
		).toBe("idempotent");

		const consumed = step(submitted, {
			type: "message_start",
			at: 130,
			message: matchingMessage(submitted),
			epochs: { message: 2 },
		});
		expect(
			transitionContinuation(consumed, {
				type: "message_start",
				at: 131,
				message: matchingMessage(consumed),
				epochs: { message: 2 },
			}).disposition,
		).toBe("idempotent");

		const done = step(consumed, {
			type: "assistant_result",
			at: 140,
			result: "progress",
			epochs: { message: 3 },
		});
		expect(
			transitionContinuation(done, {
				type: "assistant_result",
				at: 141,
				result: "progress",
				epochs: { message: 3 },
			}).disposition,
		).toBe("idempotent");
	});

	it("rejects illegal transitions, mismatched consumption, and stale epochs without regression", () => {
		const initial = created();
		expect(
			transitionContinuation(initial, {
				type: "assistant_result",
				at: 120,
				result: "progress",
			}).disposition,
		).toBe("ignored_invalid");
		expect(
			transitionContinuation(initial, { type: "submitted", at: 99 })
				.disposition,
		).toBe("ignored_stale");

		const submitted = step(initial, {
			type: "submitted",
			at: 120,
			epochs: { message: 3 },
		});
		const mismatched = {
			...matchingMessage(submitted),
			details: {
				...continuationMessageDetailsFor(submitted),
				transactionId: "tx-stale",
			},
		};
		expect(
			transitionContinuation(submitted, {
				type: "message_start",
				at: 130,
				message: mismatched,
			}).disposition,
		).toBe("ignored_invalid");
		expect(
			transitionContinuation(submitted, {
				type: "agent_start",
				at: 140,
				epochs: { message: 2 },
			}).disposition,
		).toBe("ignored_stale");
	});

	it("treats generic agent and turn starts as diagnostics rather than consumption", () => {
		const submitted = step(created(), { type: "submitted", at: 120 });
		const agent = transitionContinuation(submitted, {
			type: "agent_start",
			at: 121,
			epochs: { agent: 1 },
		});
		const turn = transitionContinuation(agent.snapshot, {
			type: "turn_start",
			at: 122,
			epochs: { turn: 1 },
		});
		expect(turn.snapshot.state).toBe("submitted");
		expect(turn.decision).toBe("none");
	});

	it("settlement without consumption retries, then fails at the absolute deadline", () => {
		const submitted = step(created(), { type: "submitted", at: 120 });
		const retry = transitionContinuation(submitted, {
			type: "agent_settled",
			at: 200,
			epochs: { settlement: 1 },
		});
		expect(retry.decision).toBe("retry");
		expect(retry.snapshot.state).toBe("retrying");
		expect(retry.snapshot.retryCount).toBe(1);

		const resubmitted = step(retry.snapshot, { type: "submitted", at: 300 });
		const failed = transitionContinuation(resubmitted, {
			type: "agent_settled",
			at: 1_100,
			epochs: { settlement: 2 },
		});
		expect(failed.decision).toBe("fail_loudly");
		expect(failed.snapshot.state).toBe("failed_loudly");
	});

	it.each([
		"error",
		"aborted",
	] as const)("terminal assistant %s after consumption is not success", (result:
		| "error"
		| "aborted") => {
		const submitted = step(created(), { type: "submitted", at: 120 });
		const consumed = step(submitted, {
			type: "message_start",
			at: 130,
			message: matchingMessage(submitted),
		});
		const terminal = step(consumed, {
			type: "assistant_result",
			at: 140,
			result,
		});
		const settled = transitionContinuation(terminal, {
			type: "agent_settled",
			at: 150,
		});
		expect(settled.snapshot.state).toBe("retrying");
		expect(settled.decision).toBe("retry");
	});

	it("only settles after progress followed by agent_settled", () => {
		const submitted = step(created(), { type: "submitted", at: 120 });
		expect(
			transitionContinuation(submitted, { type: "agent_settled", at: 130 })
				.decision,
		).not.toBe("settled");
		const consumed = step(submitted, {
			type: "message_start",
			at: 130,
			message: matchingMessage(submitted),
		});
		expect(
			transitionContinuation(consumed, { type: "agent_settled", at: 140 })
				.decision,
		).not.toBe("settled");
		expect(
			transitionContinuation(progressed(), { type: "agent_settled", at: 160 })
				.decision,
		).toBe("settled");
	});

	it("can reach each terminal state exactly once", () => {
		const terminalSnapshots = [
			step(progressed(), { type: "agent_settled", at: 160 }),
			step(created(), {
				type: "supersede",
				at: 120,
				reason: "real_user_input",
			}),
			step(created(), { type: "fail", at: 120, reason: "host_unavailable" }),
		];
		expect(terminalSnapshots.map((snapshot) => snapshot.state)).toEqual(
			CONTINUATION_TERMINAL_STATES,
		);
		for (const terminal of terminalSnapshots) {
			expect(isContinuationTerminal(terminal)).toBe(true);
			const late = transitionContinuation(terminal, {
				type: "deadline",
				at: 2_000,
			});
			expect(late.snapshot).toEqual(terminal);
			expect(late.disposition).toBe("ignored_invalid");
		}
	});

	it("starts timeout at creation, including while waiting_tools", () => {
		const waiting = step(
			created({ createdAt: 10, deadlineMs: 50, pendingToolCount: 4 }),
			{
				type: "tools_pending",
				at: 20,
				pendingToolCount: 4,
			},
		);
		expect(waiting.deadlineAt).toBe(60);
		expect(
			transitionContinuation(waiting, { type: "deadline", at: 59 }).disposition,
		).toBe("ignored_stale");
		const expired = transitionContinuation(waiting, {
			type: "deadline",
			at: 60,
		});
		expect(expired.snapshot.state).toBe("failed_loudly");
	});

	it("real input and replacement supersede without permitting later success", () => {
		const superseded = transitionContinuation(created(), {
			type: "supersede",
			at: 120,
			reason: "session_replaced",
		});
		expect(superseded.decision).toBe("superseded");
		expect(superseded.snapshot.state).toBe("superseded");
		expect(
			transitionContinuation(superseded.snapshot, {
				type: "submitted",
				at: 130,
			}).disposition,
		).toBe("ignored_invalid");
	});
});

describe("continuation persisted protocol", () => {
	it("round-trips requests, snapshots, and outcomes through JSON with strict parsing", () => {
		const request = createContinuationRequestWire(created());
		const submitted = step(request.snapshot, { type: "submitted", at: 120 });
		const snapshot = createContinuationSnapshotWire(submitted);
		const outcome = createContinuationOutcomeWire(
			step(progressed(), { type: "agent_settled", at: 160 }),
		);
		const safetyReady = createContinuationSafetyReadyWire({
			transactionId: request.snapshot.transactionId,
			attemptId: request.snapshot.attemptId,
			requestId: request.snapshot.requestId,
		});

		expect(
			parseContinuationRequest(serializeContinuationWire(request)),
		).toEqual(request);
		expect(
			parseContinuationSnapshot(serializeContinuationWire(snapshot)),
		).toEqual(snapshot);
		expect(
			parseContinuationOutcome(serializeContinuationWire(outcome)),
		).toEqual(outcome);
		expect(
			parseContinuationSafetyReady(serializeContinuationWire(safetyReady)),
		).toEqual(safetyReady);
		expect(
			parseContinuationRequest({ ...request, unexpected: true }),
		).toBeUndefined();
		expect(parseContinuationSnapshot("not json")).toBeUndefined();
		expect(
			parseContinuationOutcome({ ...outcome, transactionId: "wrong" }),
		).toBeUndefined();
	});

	it("reconciles active-branch entries in request order and deduplicates duplicate/lost wake equivalents", () => {
		const tx1 = created();
		const tx2 = created({
			transactionId: "tx-2",
			attemptId: "attempt-2",
			requestId: "request-2",
			originatingRequestId: "request-2",
		});
		const tx1Submitted = step(tx1, { type: "submitted", at: 120 });
		const tx2Terminal = step(tx2, {
			type: "supersede",
			at: 130,
			reason: "session_replaced",
		});
		const entries = [
			{
				id: "r1",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: createContinuationRequestWire(tx1),
			},
			{
				id: "r1-duplicate-wake",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: createContinuationRequestWire(tx1),
			},
			{
				id: "s1",
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: createContinuationSnapshotWire(tx1Submitted),
			},
			{
				id: "r2",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: createContinuationRequestWire(tx2),
			},
			{
				id: "o2",
				type: "custom",
				customType: CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
				data: createContinuationOutcomeWire(tx2Terminal),
			},
			{
				id: "bad",
				type: "custom",
				customType: CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
				data: { kind: "request" },
			},
		];

		const reconciled = reconcileContinuationEntries(entries);
		expect(reconciled.pending).toEqual([tx1Submitted]);
		expect(reconciled.terminal.map((wire) => wire.transactionId)).toEqual([
			"tx-2",
		]);
		expect(reconciled.duplicateRequestTransactionIds).toEqual(["tx-1"]);
		expect(reconciled.invalidEntryIds).toEqual(["bad"]);
	});

	it("reports orphan snapshots/outcomes without treating them as authoritative requests", () => {
		const orphan = created({
			transactionId: "orphan",
			attemptId: "orphan-attempt",
		});
		const terminal = step(orphan, {
			type: "fail",
			at: 120,
			reason: "invalid_persistence",
		});
		const reconciled = reconcileContinuationEntries([
			{
				type: "custom",
				customType: CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
				data: createContinuationSnapshotWire(orphan),
			},
			{
				type: "custom",
				customType: CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
				data: createContinuationOutcomeWire(terminal),
			},
		]);
		expect(reconciled.pending).toEqual([]);
		expect(reconciled.orphanSnapshotTransactionIds).toEqual(["orphan"]);
		expect(reconciled.orphanOutcomeTransactionIds).toEqual(["orphan"]);
		expect(reconciled.orphanSafetyReadyTransactionIds).toEqual([]);
	});
});

describe("initiator/outcome adapter matrix", () => {
	it("covers every package, semantic, backstop, host, no-cut, cancellation, and failure combination", () => {
		const matrix = CONTINUATION_INITIATORS.flatMap((initiator) =>
			CONTINUATION_ATTEMPT_OUTCOMES.map((outcome) =>
				adaptContinuationInitiatorOutcome(initiator, outcome),
			),
		);
		expect(matrix).toHaveLength(
			CONTINUATION_INITIATORS.length * CONTINUATION_ATTEMPT_OUTCOMES.length,
		);
		expect(
			new Set(matrix.map((entry) => `${entry.initiator}:${entry.outcome}`))
				.size,
		).toBe(matrix.length);

		for (const entry of matrix) {
			if (entry.initiator.startsWith("package-"))
				expect(entry.origin).toBe("package-command");
			if (entry.outcome === "no-safe-cut")
				expect(entry.reason).toBe("no-safe-cut");
			if (entry.outcome === "cancellation")
				expect(entry.reason).toBe("cancelled");
			if (entry.outcome === "failure") expect(entry.reason).toBe("failed");
		}
	});
});
