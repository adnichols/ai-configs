// @amp-agent-mode {"key":"adn-low","label":"ADN Low"}
// @amp-agent-mode {"key":"adn-high","label":"ADN High"}
// @amp-agent-mode {"key":"adn-alt","label":"ADN Alt"}
// @amp-agent-mode {"key":"adn-oracle","label":"ADN Oracle"}

import type { PluginAPI } from '@ampcode/plugin'

/**
 * Custom Amp modes + second-opinion tools using subscription models.
 *
 * Amp's built-in mode keys (low/medium/high/ultra) cannot be overwritten by
 * plugins. These ADN modes sit beside them in the mode picker.
 *
 * Shape mirrors Amp's product model:
 *   - ADN Low / ADN High = selectable main-thread modes
 *   - adn_oracle tool    = Sol second opinion (hard analysis / judgment)
 *   - adn_alt tool       = Grok second opinion (alternate frontier take)
 *   - ADN Oracle / ADN Alt modes = optional direct threads for those agents
 */

const MAIN_INSTRUCTIONS = [
  'You are Amp, an autonomous coding agent running one of the ADN custom modes.',
  'Inspect the relevant code before editing, make the smallest correct change,',
  'preserve unrelated user work, and verify with the narrowest useful check.',
  '',
  'Second-opinion tools:',
  '- Call adn_oracle (GPT-5.6 Sol high) for deeper analysis, architecture judgment,',
  '  subtle debugging, or independent review of a risky change.',
  '- Call adn_alt (Grok 4.5 high) when you want a different frontier model\'s take,',
  '  a contrasting second opinion, or the user asks for Grok / an alternate view.',
  'Pass each tool a focused question plus the evidence it should weigh.',
  'Do not use either tool for routine edits, simple lookups, or work you can',
  'finish cheaply yourself. Prefer an explicit user request when one is present.',
  'If both adn_oracle and Amp\'s built-in oracle tool are available, prefer adn_oracle.',
].join(' ')

const SECOND_OPINION_INSTRUCTIONS = [
  'You are a read-mostly second-opinion agent for an ADN main-thread agent.',
  'You do not own the main implementation thread.',
  'Focus on hard analysis, design tradeoffs, root-cause debugging, and review.',
  'Return concise findings: conclusion first, then evidence, risks, and a',
  'recommended next step for the main agent.',
  'Do not make broad drive-by edits. Prefer inspection and recommendations.',
  'If a tiny verification command is essential, keep it narrow and explain why.',
].join(' ')

// Keep second-opinion agents away from broad write/delegation surfaces.
// Read + shell stay available so they can inspect code and run narrow checks.
const SECOND_OPINION_TOOLS = {
  include: 'all' as const,
  exclude: [
    'create_file',
    'edit_file',
    'apply_patch',
    'Task',
    'oracle',
    'painter',
    'adn_oracle',
    'adn_alt',
  ],
}

export default function (amp: PluginAPI) {
  const low = amp.createAgent({
    name: 'adn-low',
    model: 'openai/gpt-5.6-luna',
    instructions: MAIN_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'max',
    display: { label: 'ADN Low', color: '#6b7280' },
  })

  const high = amp.createAgent({
    name: 'adn-high',
    model: 'openai/gpt-5.6-terra',
    instructions: MAIN_INSTRUCTIONS,
    tools: 'all',
    reasoningEffort: 'high',
    display: { label: 'ADN High', color: '#8b5cf6' },
  })

  const oracle = amp.createAgent({
    name: 'adn-oracle',
    model: 'openai/gpt-5.6-sol',
    instructions: [
      'You are ADN Oracle (GPT-5.6 Sol).',
      SECOND_OPINION_INSTRUCTIONS,
    ].join(' '),
    tools: SECOND_OPINION_TOOLS,
    reasoningEffort: 'high',
    display: { label: 'ADN Oracle', color: '#0f766e' },
  })

  const alt = amp.createAgent({
    name: 'adn-alt',
    model: 'xai/grok-4.5',
    instructions: [
      'You are ADN Alt (Grok 4.5), an alternate-frontier second opinion.',
      SECOND_OPINION_INSTRUCTIONS,
      'Prefer a contrasting angle from the main agent when evidence allows.',
    ].join(' '),
    tools: SECOND_OPINION_TOOLS,
    reasoningEffort: 'high',
    display: { label: 'ADN Alt', color: '#111827' },
  })

  amp.registerTool({
    name: 'adn_oracle',
    description: [
      'Ask ADN Oracle (GPT-5.6 Sol, high reasoning) for a second opinion.',
      'Use for complex analysis, architecture tradeoffs, subtle bugs, or review.',
      'Pass a self-contained request with the question and relevant evidence.',
    ].join(' '),
    inputSchema: {
      type: 'object',
      properties: {
        request: {
          type: 'string',
          description:
            'Focused oracle question plus the files, diffs, errors, or constraints to consider.',
        },
      },
      required: ['request'],
    },
    async execute(input, ctx) {
      const request = typeof input.request === 'string' ? input.request.trim() : ''
      if (!request) {
        return 'Missing ADN Oracle request.'
      }

      const result = await oracle.run(request, {
        parentThreadID: ctx.thread.id,
        timeoutMs: 10 * 60 * 1000,
      })
      return result.text
    },
  })

  amp.registerTool({
    name: 'adn_alt',
    description: [
      'Ask ADN Alt (Grok 4.5, high reasoning) for an alternate-frontier second opinion.',
      'Use when you want a contrasting take, or the user asks for Grok / an alt view.',
      'Pass a self-contained request with the question and relevant evidence.',
    ].join(' '),
    inputSchema: {
      type: 'object',
      properties: {
        request: {
          type: 'string',
          description:
            'Focused alt-opinion question plus the files, diffs, errors, or constraints to consider.',
        },
      },
      required: ['request'],
    },
    async execute(input, ctx) {
      const request = typeof input.request === 'string' ? input.request.trim() : ''
      if (!request) {
        return 'Missing ADN Alt request.'
      }

      const result = await alt.run(request, {
        parentThreadID: ctx.thread.id,
        timeoutMs: 10 * 60 * 1000,
      })
      return result.text
    },
  })

  amp.registerAgentMode({
    key: 'adn-low',
    label: 'ADN Low',
    description: 'GPT-5.6 Luna max — everyday implementation; second opinions via adn_oracle / adn_alt',
    color: '#6b7280',
    agent: low.definition,
  })

  amp.registerAgentMode({
    key: 'adn-high',
    label: 'ADN High',
    description: 'GPT-5.6 Terra high — harder implementation; second opinions via adn_oracle / adn_alt',
    color: '#8b5cf6',
    agent: high.definition,
  })

  // Optional direct modes. Prefer the tools from Low/High for second opinions
  // inside an active implementation thread.
  amp.registerAgentMode({
    key: 'adn-oracle',
    label: 'ADN Oracle',
    description: 'GPT-5.6 Sol high — direct analysis / second-opinion mode',
    color: '#0f766e',
    agent: oracle.definition,
  })

  amp.registerAgentMode({
    key: 'adn-alt',
    label: 'ADN Alt',
    description: 'Grok 4.5 high — direct alternate-frontier mode',
    color: '#111827',
    agent: alt.definition,
  })
}
