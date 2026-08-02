// @amp-agent-mode {"key":"adn-low","label":"ADN Low"}
// @amp-agent-mode {"key":"adn-med","label":"ADN Med"}
// @amp-agent-mode {"key":"adn-high","label":"ADN High"}
// @amp-agent-mode {"key":"adn-ultra","label":"ADN Ultra"}
// @amp-agent-mode {"key":"grok45","label":"Grok 4.5"}

import type { PluginAPI } from '@ampcode/plugin'

const CODING_INSTRUCTIONS = [
  'You are Amp, an autonomous coding agent.',
  'Inspect the relevant code before editing, make the smallest correct change,',
  'preserve unrelated user work, and verify the result with the narrowest useful check.',
].join(' ')

const DEEP_INSTRUCTIONS = [
  CODING_INSTRUCTIONS,
  'Use deeper analysis for difficult debugging, architecture, planning, and review tasks.',
  'Explain material tradeoffs and carry implementation through verification when authorized.',
].join(' ')

export default function (amp: PluginAPI) {
  // ── Tier: Low ──────────────────────────────────────────────────────
  // Main: GPT-5.6 Terra (fast/cheap — DeepSeek-V4-Flash requested but not
  //       supported by Amp's built-in provider list)
  // Oracle: spawn a GPT-5.6 Sol sub-agent for deeper analysis when needed
  const low = amp.createAgent({
    name: 'adn-low',
    model: 'openai/gpt-5.6-terra',
    instructions: CODING_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'low',
    display: { label: 'ADN Low', color: '#6b7280' },
  })

  // ── Tier: Med ──────────────────────────────────────────────────────
  // Main: Grok 4.5
  // Oracle: spawn GPT-5.6 Sol sub-agent for second opinions
  const med = amp.createAgent({
    name: 'adn-med',
    model: 'xai/grok-4.5',
    instructions: CODING_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'medium',
    display: { label: 'ADN Med', color: '#f59e0b' },
  })

  // ── Tier: High ─────────────────────────────────────────────────────
  // Main: GPT-5.6 Sol (high reasoning)
  // Secondary Oracle / review: spawn Grok 4.5 sub-agent
  const high = amp.createAgent({
    name: 'adn-high',
    model: 'openai/gpt-5.6-sol',
    instructions: DEEP_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'high',
    display: { label: 'ADN High', color: '#8b5cf6' },
  })

  // ── Tier: Ultra ────────────────────────────────────────────────────
  // Main: GPT-5.6 Sol (max reasoning)
  // Second opinion: spawn GPT-5.6 Sol or Grok sub-agent
  const ultra = amp.createAgent({
    name: 'adn-ultra',
    model: 'openai/gpt-5.6-sol',
    instructions: DEEP_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'max',
    display: { label: 'ADN Ultra', color: '#ef4444' },
  })

  // ── Standalone Grok 4.5 (kept for direct use) ─────────────────────
  const grok = amp.createAgent({
    name: 'grok-4-5',
    model: 'xai/grok-4.5',
    instructions: DEEP_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'high',
    display: { label: 'Grok 4.5', color: '#111827' },
  })

  // ── Register modes ─────────────────────────────────────────────────
  amp.registerAgentMode({
    key: 'adn-low',
    label: 'ADN Low',
    description: 'GPT-5.6 Terra fast/cheap — Oracle: GPT-5.6 Sol when needed',
    agent: low.definition,
  })

  amp.registerAgentMode({
    key: 'adn-med',
    label: 'ADN Med',
    description: 'Grok 4.5 (balanced) — Oracle: GPT-5.6 Sol',
    agent: med.definition,
  })

  amp.registerAgentMode({
    key: 'adn-high',
    label: 'ADN High',
    description: 'GPT-5.6 Sol high reasoning — Review: Grok 4.5',
    agent: high.definition,
  })

  amp.registerAgentMode({
    key: 'adn-ultra',
    label: 'ADN Ultra',
    description: 'GPT-5.6 Sol max reasoning — Second opinion: GPT-5.6 Sol or Grok',
    agent: ultra.definition,
  })

  amp.registerAgentMode({
    key: 'grok45',
    label: 'Grok 4.5',
    description: 'Grok 4.5 with high reasoning via your xAI subscription',
    agent: grok.definition,
  })
}
