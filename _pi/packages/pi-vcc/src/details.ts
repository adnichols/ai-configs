import type { CompactionIntent, CompactionReason, CompactionResumeIntent } from "./types";

export interface PiVccCompactionDetails {
  compactor: "pi-vcc";
  version: number;
  sections: string[];
  sourceMessageCount: number;
  previousSummaryUsed: boolean;
  interruptedInFlightTurn?: boolean;
  requiresContinuation?: boolean;
  reason?: CompactionReason;
  willRetry?: boolean;
  compactionIntent?: CompactionIntent;
  retainedNonMessageEntries?: boolean;
  continuationAttemptId?: string;
  continuationRequestId?: string;
  continuationTransactionId?: string;
  compactionResumeIntent?: CompactionResumeIntent;
  continuationResumePolicy?: "active" | "terminal";
}
