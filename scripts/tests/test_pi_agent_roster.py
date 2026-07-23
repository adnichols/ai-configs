import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "_pi" / "agents"
EXPECTED_FILES = {"Explore.md", "planner.md", "reviewer.md", "scout.md"}
EXPECTED_ROUTES = {
    "planner": ("openai-codex/gpt-5.6-sol", "medium"),
    "reviewer": ("openai-codex/gpt-5.6-sol", "medium"),
    "scout": ("openai-codex/gpt-5.6-terra", "low"),
}
RETIRED_PERSONAS = {
    "developer-high", "developer-mid", "developer-mm", "multi-reviewer", "plan-gpt",
    "prd-critical-thinker", "quality-reviewer", "research", "researcher",
    "reviewer-gemini", "reviewer-gpt", "reviewer-opus",
    "reviewer-plan-adversarial-gpt", "reviewer-plan-adversarial-opus",
    "reviewer-plan-gpt", "reviewer-plan-opus", "reviewer-plan-synthesis",
    "reviewer-prd-dependencies", "reviewer-prd-intent",
    "reviewer-prd-product-principles", "reviewer-prd-scope-stage-fit",
    "reviewer-prd-security-privacy-reliability", "worker", "worktree-creator",
}
NON_ROSTER_ROUTES = RETIRED_PERSONAS | {"debugger", "explore", "general"}


def frontmatter(path):
    text = path.read_text()
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise AssertionError(f"missing frontmatter: {path.relative_to(ROOT)}")
    values = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values, text[match.end():]


class PiAgentRosterTest(unittest.TestCase):
    maxDiff = None

    def test_exact_source_roster_and_model_effort_mapping(self):
        self.assertEqual(EXPECTED_FILES, {path.name for path in AGENTS.glob("*.md")})
        explore, _ = frontmatter(AGENTS / "Explore.md")
        self.assertEqual("false", explore.get("enabled"))
        for name, (model, effort) in EXPECTED_ROUTES.items():
            metadata, _ = frontmatter(AGENTS / f"{name}.md")
            self.assertEqual(name, metadata.get("name"))
            self.assertEqual("subagent", metadata.get("mode"))
            self.assertEqual(model, metadata.get("model"))
            self.assertEqual(effort, metadata.get("reasoningEffort"))
            self.assertNotIn("thinking", metadata)
            self.assertNotIn("output", metadata)
            self.assertNotIn("defaultReads", metadata)

    def test_prompts_keep_generic_authority_and_stop_rules(self):
        bodies = {name: frontmatter(AGENTS / f"{name}.md")[1].lower() for name in EXPECTED_ROUTES}
        for name, body in bodies.items():
            self.assertIn("scope", body, name)
            self.assertIn("evidence", body, name)
            self.assertRegex(body, r"verif(?:y|ied|ication)", name)
            self.assertRegex(body, r"stop|blocker", name)
            self.assertNotRegex(body, r"thoughts/|claude\.md|prd-|plan\.md|context\.md", name)
        self.assertFalse((AGENTS / "developer-mid.md").exists())
        self.assertIn("planning-only", bodies["planner"])
        self.assertIn("do not modify", bodies["planner"])
        self.assertIn("read-only", bodies["scout"])
        self.assertIn("web", bodies["scout"])
        self.assertIn("read-only", bodies["reviewer"])
        self.assertIn("material", bodies["reviewer"])
        self.assertRegex(bodies["reviewer"], r"explicit.*review artifact")
        self.assertIn("caller-authorized annotations", bodies["reviewer"])
        self.assertIn("beyond that granted output contract", bodies["reviewer"])

    def test_development_stays_in_driving_session(self):
        retired_claude_agents = {
            ROOT / "_claude" / "agents" / "developer.md",
            ROOT / "_claude" / "agents" / "developer-fidelity.md",
            ROOT / "_claude" / "agents" / "worktree-creator.md",
        }
        self.assertTrue(all(not path.exists() for path in retired_claude_agents))

        doctrine = (ROOT / "APPEND_SYSTEM.md").read_text().lower()
        self.assertIn("driving agent owns development work directly", doctrine)
        self.assertIn("do not delegate code edits", doctrine)

        surfaces = [
            ROOT / "_pi" / "prompts",
            ROOT / "_codex" / "prompts",
            ROOT / "_claude" / "commands",
            ROOT / "skills",
        ]
        forbidden = re.compile(
            r"developer-mid|developer-fidelity|developer-mm|"
            r"subagent_type\s*[:=]\s*[\"']?developer(?:-[a-z0-9-]+)?|"
            r"delegate all implementation|always prefer a sub-agent when making changes",
            re.I,
        )
        violations = []
        for surface in surfaces:
            for path in sorted(p for p in surface.rglob("*") if p.suffix in {".md", ".json"}):
                for match in forbidden.finditer(path.read_text(errors="replace")):
                    line = path.read_text(errors="replace").count("\n", 0, match.start()) + 1
                    violations.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")
        self.assertEqual([], violations)

    def test_development_stays_in_driving_session(self):
        retired_claude_agents = {
            ROOT / "_claude" / "agents" / "developer.md",
            ROOT / "_claude" / "agents" / "developer-fidelity.md",
            ROOT / "_claude" / "agents" / "worktree-creator.md",
        }
        self.assertTrue(all(not path.exists() for path in retired_claude_agents))

        doctrine = (ROOT / "APPEND_SYSTEM.md").read_text().lower()
        self.assertIn("driving agent owns development work directly", doctrine)
        self.assertIn("do not delegate code edits", doctrine)

        surfaces = [
            ROOT / "_pi" / "prompts",
            ROOT / "_codex" / "prompts",
            ROOT / "_claude" / "commands",
            ROOT / "skills",
        ]
        forbidden = re.compile(
            r"developer-mid|developer-fidelity|developer-mm|"
            r"subagent_type\s*[:=]\s*[\"']?developer(?:-[a-z0-9-]+)?|"
            r"delegate all implementation|always prefer a sub-agent when making changes",
            re.I,
        )
        violations = []
        for surface in surfaces:
            for path in sorted(p for p in surface.rglob("*") if p.suffix in {".md", ".json"}):
                for match in forbidden.finditer(path.read_text(errors="replace")):
                    line = path.read_text(errors="replace").count("\n", 0, match.start()) + 1
                    violations.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")
        self.assertEqual([], violations)

    def test_scout_caller_packets_are_bounded_and_evidence_only(self):
        prompts = {
            "cmd:debug": (
                ROOT / "_pi" / "prompts" / "cmd:debug.md",
                "When parallel evidence gathering would materially reduce context or latency",
                "\nDo not delegate the whole investigation.",
            ),
            "dev:run": (
                ROOT / "_pi" / "prompts" / "dev:run.md",
                "Use `scout` before implementation whenever target files or contracts are not already known.",
                "\n\nThe driving agent performs all implementation directly",
            ),
            "prd:clarify-round": (
                ROOT / "_pi" / "prompts" / "prd:clarify-round.md",
                "For each scout call,",
                "\n\n## Phase 4: Next-Step Decision",
            ),
        }
        for name, (path, start, end) in prompts.items():
            source = path.read_text()
            with self.subTest(prompt=name):
                self.assertEqual(1, source.count(start), f"ambiguous start anchor: {start}")
                self.assertEqual(1, source.count(end), f"ambiguous end anchor: {end}")
                text = source.split(start, 1)[1].split(end, 1)[0].lower()
                self.assertIn("one evidence question", text)
                self.assertRegex(text, r"allowed[^\n]*(?:files|directories|surfaces|sources)")
                self.assertIn("read-only", text)
                self.assertRegex(text, r"no edits|do not edit|must not edit|modify files")
                self.assertIn("evidence", text)
                self.assertIn("citations", text)
                self.assertRegex(text, r"directly to (?:the|this) driving session")
                self.assertRegex(text, r"no artifact|create no artifact")
                self.assertIn("blocker", text)
                self.assertIn("stop", text)
                self.assertRegex(
                    text,
                    r"no [^\n.]*recommendations|do not [^\n.]*recommend|must not [^\n.]*recommend",
                )
                self.assertRegex(
                    text,
                    r"no [^\n.]*synthesis|do not [^\n.]*synthesi[sz]e|must not [^\n.]*synthesi[sz]e",
                )

    def test_start_linear_issue_source_contract(self):
        prompt = (ROOT / "_pi" / "prompts" / "cmd:start-linear-issue.md").read_text()
        self.assertIn("Second argument: `BASE_BRANCH` (optional), default `origin/main`.", prompt)
        self.assertIn('ISSUE_LOWER=$(printf \'%s\' "$ISSUE_KEY" | tr \'[:upper:]\' \'[:lower:]\')', prompt)
        self.assertIn('BRANCH_NAME="$ISSUE_LOWER"', prompt)
        self.assertIn('WORKTREE_PATH="$REPO_PARENT/${REPO_NAME}-${ISSUE_LOWER}"', prompt)
        self.assertIn('BASE_REF="${BASE_BRANCH:-origin/main}"', prompt)
        self.assertIn("does not exactly match the issue Project, stop before creating a branch or worktree", prompt)
        self.assertIn("Continue only after explicit confirmation; do not treat silence as approval.", prompt)
        self.assertIn("- Title", prompt)
        self.assertIn("# <ISSUE_KEY>: <Title>", prompt)
        for field in ("**URL**:", "**Project**:", "**State**:", "**Branch**:",
                      "**Worktree**:", "**Base**:", "**Created**:", "## Description"):
            self.assertIn(field, prompt)
        for field in ("Location:", "Branch:", "Linear:", "Context note:", "Base/upstream:"):
            self.assertIn(field, prompt)
        for collision in ("refs/heads/${BRANCH_NAME}", "refs/remotes/origin/${BRANCH_NAME}",
                          "`WORKTREE_PATH` exists as any filesystem entry",
                          "git worktree list --porcelain"):
            self.assertIn(collision, prompt)
        self.assertIn("Fail closed at the first unsafe or ambiguous condition.", prompt)
        self.assertIn("Never force-remove, overwrite, reset, or delete user work.", prompt)
        self.assertNotIn("git worktree remove --force", prompt)
        self.assertNotIn("git branch -D", prompt)
        self.assertNotIn("rm -rf \"$WORKTREE_PATH\"", prompt)

    def test_retired_gpt_54_models_are_absent(self):
        source = json.loads((ROOT / "_pi" / "models.json").read_text())
        models = source["providers"]["openai-codex"]["models"]
        self.assertTrue(all(model.get("id") not in {"gpt-5.4", "gpt-5.4-mini"} for model in models))
        for path in AGENTS.glob("*.md"):
            self.assertNotRegex(path.read_text(), r"gpt-5\.4(?:-mini)?")

    def test_maintained_workflows_have_no_non_roster_routes(self):
        surfaces = [ROOT / "_pi" / "prompts", ROOT / "_pi" / "extensions"]
        retired_names = "|".join(re.escape(name) for name in sorted(NON_ROSTER_ROUTES, key=len, reverse=True))
        patterns = [
            re.compile(r"^agent:\s*([a-z0-9-]+)\s*$", re.M),
            re.compile(r"subagent_type\s*[:=]\s*[\"']?([A-Za-z0-9-]+)"),
            re.compile(rf"@?\b({retired_names})\b\s+(?:agent|sub-?agent|persona)\b", re.I),
            re.compile(rf"\b(?:agent|sub-?agent|persona)\b\s+(?:named\s+)?({retired_names})\b", re.I),
        ]
        violations = []
        for surface in surfaces:
            for path in sorted(p for p in surface.rglob("*") if p.suffix in {".md", ".js", ".mjs", ".ts"}):
                text = path.read_text(errors="replace")
                for pattern in patterns:
                    for match in pattern.finditer(text):
                        route = match.group(1).lower()
                        if route in NON_ROSTER_ROUTES:
                            line = text.count("\n", 0, match.start()) + 1
                            violations.append(f"{path.relative_to(ROOT)}:{line}: {route}")
        self.assertEqual([], sorted(set(violations)))


if __name__ == "__main__":
    unittest.main()
