import {
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  type ContinuationTransactionSnapshot,
  isMatchingContinuationDetails,
} from "./continuation-protocol";

export const STATUS_ONLY_CUSTOM_MESSAGE_TYPES = ["ad-process:update"] as const;
export const MODEL_DRIVING_CUSTOM_MESSAGE_TYPES = [
  "vcc-recall",
  "claude-review-completion",
  "compaction-nudge",
] as const;

export type CustomMessageIntent = "continuation" | "status" | "independent";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const classifyCustomMessageIntent = (
  message: unknown,
  snapshot: ContinuationTransactionSnapshot,
): CustomMessageIntent => {
  if (!isRecord(message)) return "independent";
  if (
    message.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE &&
    isMatchingContinuationDetails(snapshot, message.details)
  ) return "continuation";

  const details = isRecord(message.details) ? message.details : undefined;
  if (
    details?.piVccInputIntent === "independent" ||
    details?.piVccInputIntent === "replace-continuation"
  ) return "independent";
  if (details?.piVccInputIntent === "status") return "status";
  if (
    typeof message.customType === "string" &&
    (STATUS_ONLY_CUSTOM_MESSAGE_TYPES as readonly string[]).includes(message.customType)
  ) return "status";

  // Known model-driving types and every unknown/unmarked custom message
  // intentionally fail closed. The exported list is the audited producer
  // contract even though the fallback has the same result.
  return "independent";
};
