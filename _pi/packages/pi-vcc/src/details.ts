import type { CompactionIntent, CompactionReason } from "./types";

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
}
