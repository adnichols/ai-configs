const PROVIDER_ERROR_PATTERNS = [
  /^provider\s+error(?:\s|:)/i,
  /^tool(?:-only| only)\b/i,
  /^no final (?:review|answer|response) was produced\b/i,
  /^(?:api|authentication|rate limit|session limit) error(?:\s|:)/i,
];

function normalizedReviewParts(text) {
  const normalized = text.replace(/\r/g, "");
  const metadataIndex = normalized.indexOf("CLAUDE_REVIEW_LAUNCHER_METADATA");
  const answer = metadataIndex >= 0
    ? normalized.slice(0, metadataIndex).replace(/(?:\n|^)---\s*$/, "").trim()
    : "";
  const metadata = metadataIndex >= 0 ? normalized.slice(metadataIndex) : "";
  return { normalized, answer, metadata, metadataIndex };
}

export function classifyArtifact(action, text) {
  const { normalized, answer, metadata, metadataIndex } = normalizedReviewParts(text);
  const firstCode = normalized.match(/^\s*(CLAUDE_[A-Z0-9_]+)/)?.[1];
  if (firstCode && firstCode !== "CLAUDE_REVIEW_SMOKE_READY" && firstCode !== "CLAUDE_REVIEW_LAUNCHER_METADATA") {
    return { ok: false, classification: firstCode };
  }
  if (action === "smoke") {
    const ok = normalized.includes("CLAUDE_REVIEW_SMOKE_READY")
      && /^socket=.+$/m.test(normalized)
      && /^session=.+$/m.test(normalized);
    return { ok, classification: ok ? "CLAUDE_REVIEW_SMOKE_READY" : "CLAUDE_REVIEW_ARTIFACT_INVALID" };
  }

  const metadataPresent = metadataIndex >= 0
    && /^CLAUDE_REVIEW_LAUNCHER_METADATA\s*$/m.test(metadata)
    && /^socket=.+$/m.test(metadata)
    && /^session=.+$/m.test(metadata);
  const providerOrToolOnly = PROVIDER_ERROR_PATTERNS.some((pattern) => pattern.test(answer));
  const promptTemplate = /Claude review launcher emission protocol|<review text here>/.test(answer);
  const ok = metadataPresent && answer.length > 0 && !providerOrToolOnly && !promptTemplate;
  return { ok, classification: ok ? "CLAUDE_REVIEW_SUCCEEDED" : "CLAUDE_REVIEW_ARTIFACT_INVALID" };
}
