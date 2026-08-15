/**
 * Historical continuation messages are retained for recall, but are never
 * executable. This predicate is intentionally tiny: there is no runtime
 * state, rehydration, timer, or send path behind the old record family.
 */
export const LEGACY_CONTINUATION_MESSAGE_TYPE = "pi-vcc-continuation" as const;

export const isLegacyContinuationMessage = (message: unknown): boolean =>
	Boolean(
		message &&
		typeof message === "object" &&
		(message as { customType?: unknown }).customType === LEGACY_CONTINUATION_MESSAGE_TYPE,
	);
