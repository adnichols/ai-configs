import type { TranscriptEntry } from "./core/brief";

export interface SectionData {
  sessionGoal: string[];
  compactionIntent: string[];
  outstandingContext: string[];
  filesAndChanges: string[];
  userPreferences: string[];
  briefTranscript: string;
  /** Structured transcript entries (verbose object format) */
  transcriptEntries: TranscriptEntry[];
}
