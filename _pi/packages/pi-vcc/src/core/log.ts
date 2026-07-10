import { appendFileSync, mkdirSync } from "fs";
import { homedir } from "os";
import { dirname, join } from "path";
import {
  continuationLogRecordFor,
  isStrictContinuationLogRecord,
  type ContinuationLogEvent,
} from "./log-schema";
import type { ContinuationTransactionSnapshot } from "./continuation-protocol";

export const PI_VCC_LOG_PATH = join(homedir(), ".pi", "logs", "pi-vcc.jsonl");

export const getPiVccLogPath = () => process.env.PI_VCC_LOG_PATH?.trim() || PI_VCC_LOG_PATH;

const SECRET_KEY_PATTERN = /(^|[_-])(token|secret|authorization|password|api[_-]?key|apikey)($|[_-])/i;
const SECRET_VALUE_PATTERN = /\b(Bearer\s+)[A-Za-z0-9._~+/=-]+|\b(sk-[A-Za-z0-9_-]{12,})\b/g;

const scrubText = (value: string): string =>
  value.length > 4000
    ? value.slice(0, 4000).replace(SECRET_VALUE_PATTERN, "$1[redacted]") + "…[truncated]"
    : value.replace(SECRET_VALUE_PATTERN, "$1[redacted]");

const serializeError = (err: unknown) => {
  if (err instanceof Error) {
    return {
      name: err.name,
      message: scrubText(err.message),
      stack: err.stack ? scrubText(err.stack) : undefined,
    };
  }
  return { message: scrubText(String(err)) };
};

export const safePiVccLogJson = (value: unknown): unknown => {
  if (value instanceof Error) return serializeError(value);
  if (typeof value === "string") return scrubText(value);
  if (Array.isArray(value)) return value.map(safePiVccLogJson);
  if (value instanceof Set) return [...value].map(safePiVccLogJson);
  if (value instanceof Map) {
    return Object.fromEntries([...value].map(([key, raw]) => [String(key), safePiVccLogJson(raw)]));
  }
  if (!value || typeof value !== "object") return value;
  const output: Record<string, unknown> = {};
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    if (SECRET_KEY_PATTERN.test(key)) {
      output[key] = "[redacted]";
      continue;
    }
    output[key] = safePiVccLogJson(raw);
  }
  return output;
};

export const logPiVccEvent = (event: string, data: Record<string, unknown> = {}) => {
  try {
    const logPath = getPiVccLogPath();
    mkdirSync(dirname(logPath), { recursive: true });
    appendFileSync(
      logPath,
      JSON.stringify({
        timestamp: new Date().toISOString(),
        event,
        cwd: process.cwd(),
        ...safePiVccLogJson(data) as Record<string, unknown>,
      }) + "\n",
    );
  } catch {
    // Logging must never interfere with compaction or recovery.
  }
};

export const logPiVccError = (event: string, err: unknown, data: Record<string, unknown> = {}) => {
  logPiVccEvent(event, { ...data, error: serializeError(err) });
};

export const logContinuationTransaction = (
  event: ContinuationLogEvent,
  snapshot: ContinuationTransactionSnapshot,
  now = Date.now(),
) => {
  try {
    const record = continuationLogRecordFor(event, snapshot, now);
    if (!isStrictContinuationLogRecord(record)) throw new TypeError("Invalid continuation transaction log record");
    const logPath = getPiVccLogPath();
    mkdirSync(dirname(logPath), { recursive: true });
    appendFileSync(logPath, JSON.stringify(record) + "\n");
  } catch {
    // Logging must never interfere with compaction or recovery.
  }
};
