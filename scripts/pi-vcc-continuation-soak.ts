import { appendFileSync, mkdirSync } from "fs";
import { pathToFileURL } from "url";
import { join, resolve } from "path";

const candidate = resolve(process.env.PI_VCC_CANDIDATE_PATH ?? "_pi/packages/pi-vcc");
const root = resolve(process.env.PI_VCC_SOAK_ROOT ?? ".");
const count = Number(process.env.PI_VCC_SOAK_COMPACTIONS ?? "10");
const continuation = await import(pathToFileURL(join(candidate, "src/core/continuation.ts")).href);
const protocol = await import(pathToFileURL(join(candidate, "src/core/continuation-protocol.ts")).href);
const logSchema = await import(pathToFileURL(join(candidate, "src/core/log-schema.ts")).href);

mkdirSync(join(root, "sessions"), { recursive: true });
mkdirSync(join(root, "logs"), { recursive: true });
const sessionPath = join(root, "sessions", "soak.jsonl");
const logPath = join(root, "logs", "pi-vcc.jsonl");
appendFileSync(sessionPath, JSON.stringify({ type: "session", version: 3, id: "pi-vcc-soak", timestamp: new Date(0).toISOString(), cwd: root }) + "\n");

const appendEntry = (customType: string, data: unknown, index: number) => appendFileSync(sessionPath, JSON.stringify({
  type: "custom",
  id: `entry-${index}`,
  parentId: null,
  timestamp: new Date(index).toISOString(),
  customType,
  data,
}) + "\n");

for (let index = 0; index < count; index += 1) {
  const createdAt = 1000 + index * 100;
  let snapshot = continuation.createContinuationTransaction({
    transactionId: `soak-tx-${index}`,
    origin: index % 3 === 0 ? "compact_context" : index % 3 === 1 ? "hard-backstop" : "package-command",
    reason: index % 4 === 1 ? "cancelled" : index % 4 === 2 ? "no-safe-cut" : index % 4 === 3 ? "failed" : "compacted",
    compactionId: `compact-${index}`,
    attemptId: `attempt-${index}`,
    requestId: `request-${index}`,
    originatingRequestId: `request-${index}`,
    resumePolicy: "active",
    createdAt,
    deadlineMs: 100,
    retryLimit: 1,
    pendingToolCount: index === 8 ? 1 : 0,
  });
  appendEntry(protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, protocol.createContinuationRequestWire(snapshot), index * 4 + 1);
  const apply = (event: any) => { snapshot = continuation.transitionContinuation(snapshot, event).snapshot; };

  if (index === 8) {
    apply({ type: "tools_pending", at: createdAt, pendingToolCount: 1 });
    apply({ type: "deadline", at: createdAt + 100 });
  } else if (index === 6) {
    apply({ type: "supersede", at: createdAt + 10, reason: "real_user_input" });
  } else if (index === 7) {
    apply({ type: "supersede", at: createdAt + 10, reason: "session_replaced" });
  } else {
    apply({ type: "submitted", at: createdAt + 10 });
    if (index === 4) {
      apply({ type: "agent_settled", at: createdAt + 20 });
      apply({ type: "submitted", at: createdAt + 30 });
    }
    apply({
      type: "message_start",
      at: createdAt + 40,
      message: {
        role: "custom",
        customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
        details: protocol.continuationMessageDetailsFor(snapshot),
      },
    });
    if (index === 5) {
      apply({ type: "assistant_result", at: createdAt + 50, result: "error" });
      apply({ type: "agent_settled", at: createdAt + 60 });
      apply({ type: "submitted", at: createdAt + 70 });
      apply({
        type: "message_start",
        at: createdAt + 75,
        message: {
          role: "custom",
          customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
          details: protocol.continuationMessageDetailsFor(snapshot),
        },
      });
    }
    apply({ type: "assistant_result", at: createdAt + 80, result: "progress" });
    apply({ type: "agent_settled", at: createdAt + 90 });
  }

  if (!continuation.isContinuationTerminal(snapshot)) throw new Error(`nonterminal soak transaction ${snapshot.transactionId}`);
  appendEntry(protocol.CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE, protocol.createContinuationOutcomeWire(snapshot), index * 4 + 2);
  const event = snapshot.state === "failed_loudly" ? "failed" : snapshot.state;
  const record = logSchema.continuationLogRecordFor(event, snapshot, createdAt + 100);
  if (!logSchema.isStrictContinuationLogRecord(record)) throw new Error(`invalid log record ${snapshot.transactionId}`);
  appendFileSync(logPath, JSON.stringify(record) + "\n");
}

console.log(`pi-vcc continuation soak: ${count} terminal transactions using ${candidate}`);
console.log(`session=${sessionPath}`);
console.log(`log=${logPath}`);
