export type Route = {
  playbook: string;
  active: boolean;
  handoff?: string;
  deliveryArmed: false;
  reason?: string;
  todos?: string[];
  threshold?: string;
};

const FORMAL: Array<{ threshold: string; re: RegExp }> = [
  { threshold: "multi-pr-or-cross-repo", re: /\b(multi[- ]pr|cross[- ]repos?|several pull requests)\b/i },
  { threshold: "expensive-schema-persistence-api", re: /\b(schema|persistence|public[- ]api)\b.*\b(migrat|overhaul)\b|\bmigrat\w+ .*\b(schema|persistence|public[- ]api)\b/i },
  { threshold: "exceeds-one-session", re: /\b(exceeds? one (agent )?session|multi[- ]session|more than one session)\b/i },
  { threshold: "unattended-audit-trail", re: /\b(unattended|audit trail)\b/i },
  { threshold: "several-production-subsystems", re: /\b(several production subsystems|cross[- ]subsystem)\b/i },
  { threshold: "explicit-plan-or-delivery", re: /\b(\/dev:plan|\/run-plan|reviewed-html-plan|explicit (plan|delivery) request)\b/i },
];

const PLAYBOOKS: Array<{ playbook: string; re: RegExp; todos?: string[] }> = [
  { playbook: "investigation", re: /\b(investigat\w*|how does|why (was|is)|read-only)\b/i, todos: ["how", "cite"] },
  { playbook: "perf-issue", re: /\bperf(ormance)?\b/i },
  { playbook: "hillclimb", re: /\bhillclimb\b/i },
  { playbook: "runtime-forensics", re: /\bruntime forensics\b/i },
  { playbook: "trace-forensics", re: /\btrace forensics\b/i },
  { playbook: "feature", re: /\b(feature|add --json|new behavior)\b/i, todos: ["data-shape", "implement", "smoke"] },
  { playbook: "refactoring", re: /\brefactor/i, todos: ["lock-behavior", "cutover", "prove"] },
  { playbook: "prototype", re: /\bprototype\b/i },
  { playbook: "visual-parity", re: /\bvisual parity\b/i },
  { playbook: "authoring-a-skill", re: /\bauthoring a skill\b/i },
  { playbook: "eval", re: /\beval\b/i },
  { playbook: "babysit", re: /\bbabysit\b/i },
  { playbook: "shipping", re: /\bshipping\b/i },
  { playbook: "autonomous-run", re: /\bautonomous run\b/i },
  { playbook: "orchestrate", re: /\borchestrate\b/i },
  { playbook: "autopilot-full", re: /\bautopilot full\b/i },
  { playbook: "autopilot-stack", re: /\bautopilot[- ]stack\b/i },
  { playbook: "session-pickup", re: /\bsession pickup\b/i },
  { playbook: "pause-safely", re: /\bpause safely\b/i },
  { playbook: "worktree-cleanup", re: /\bworktree cleanup\b/i },
  { playbook: "opening-a-pr", re: /\bopening a pr\b/i },
  { playbook: "bug-fix", re: /\b(bug|defect|fix|reproduc)/i, todos: ["reproduce", "root-cause", "fix", "smoke"] },
];
const CASUAL = /^(hi|hey|thanks|ok|okay|lol|cool)\.?$/i;

export function routeRequest(input: { text: string; adnActive: boolean; explicitAdn?: boolean }): Route {
  const text = input.text.trim();
  if (!input.adnActive && !input.explicitAdn) {
    return { playbook: "none", active: false, deliveryArmed: false, reason: "outside-adn" };
  }
  if (CASUAL.test(text)) {
    return { playbook: "none", active: false, deliveryArmed: false, reason: "casual" };
  }
  for (const row of FORMAL) {
    if (row.re.test(text)) {
      return {
        playbook: "multi-phase-plan",
        active: true,
        handoff: "reviewed-html-plan",
        deliveryArmed: false,
        threshold: row.threshold,
      };
    }
  }
  for (const row of PLAYBOOKS) {
    if (row.re.test(text)) {
      return { playbook: row.playbook, active: true, deliveryArmed: false, todos: row.todos };
    }
  }
  return { playbook: "figure-it-out", active: true, deliveryArmed: false, reason: "no-fit" };
}

if (import.meta.main) {
  const text = process.argv.slice(2).join(" ");
  console.log(JSON.stringify(routeRequest({ text, adnActive: true })));
}
