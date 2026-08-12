import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "_pi" / "agents"
EXPECTED_FILES = {"Explore.md", "imaging.md", "oracle.md", "planner.md", "reviewer.md", "scout.md"}
EXPECTED_ROUTES = {
    "oracle": ("openai-codex/gpt-5.6-sol", "high"),
    "planner": ("openai-codex/gpt-5.6-sol", "medium"),
    "reviewer": ("openai-codex/gpt-5.6-terra", "medium"),
    "scout": ("openai-codex/gpt-5.6-terra", "low"),
    "imaging": ("openai-codex/gpt-5.6-luna", "xhigh"),
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
            if name == "oracle":
                self.assertEqual("high", metadata.get("thinking"))
                self.assertEqual("fork", metadata.get("defaultContext"))
            elif name == "imaging":
                self.assertEqual("xhigh", metadata.get("thinking"))
                self.assertNotIn("defaultContext", metadata)
            else:
                self.assertNotIn("thinking", metadata)
                self.assertNotIn("defaultContext", metadata)
            self.assertNotIn("output", metadata)
            self.assertNotIn("defaultReads", metadata)

    def test_pi_model_scope_and_default_route(self):
        allowlist = (ROOT / "_pi" / "extensions" / "model-allowlist.ts").read_text()
        for model in (
            "openai-codex/gpt-5.6-terra",
            "openai-codex/gpt-5.6-luna",
            "openai-codex/gpt-5.6-sol",
            "xai/grok-4.6",
            "cursor/grok-4.6",
            "opencode/deepseek-v4-flash",
            "synthetic/hf:moonshotai/Kimi-K3",
            "fireworks/accounts/fireworks/models/deepseek-v4-flash-0731",
            "fireworks/accounts/fireworks/models/kimi-k3",
            "deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731",
            "deepinfra/zai-org/GLM-5.2",
        ):
            self.assertIn(f'"{model}"', allowlist)
        for excluded in (
            "opencode/glm-5.2",
            "xai/grok-4.3",
            "xai/grok-4.5",
            "xai/grok-build-0.1",
            "cursor/grok-4.5",
            "cursor/grok-4.5:fast",
            "cursor/grok-4.5:slow",
            "cursor/grok-4.6:fast",
            "cursor/grok-4.6:slow",
            "cursor/composer-2.5",
            "opencode/deepseek-v4-pro",
        ):
            self.assertNotIn(f'"{excluded}"', allowlist)
        self.assertIn("await registry.refresh({ allowNetwork: false })", allowlist)
        self.assertIn("getAvailable(provider, options)", allowlist)
        self.assertNotIn("forceRefreshAvailability", allowlist)
        models = json.loads((ROOT / "_pi" / "models.json").read_text())
        managed_ids = {item["id"] for item in models["providers"]["openai-codex"]["models"]}
        self.assertIn("gpt-5.6-sol", managed_ids)
        self.assertIn("gpt-5.6-terra", managed_ids)
        self.assertNotIn("grok-4.5", managed_ids)
        grok_46 = next(item for item in models["providers"]["xai"]["models"] if item["id"] == "grok-4.6")
        self.assertEqual(200000, grok_46["contextWindow"])
        self.assertEqual(200000, grok_46["maxTokens"])
        self.assertEqual({"grok-4.6"}, {item["id"] for item in models["providers"]["xai"]["models"]})
        self.assertNotIn("opencode-go", models["providers"])
        self.assertNotIn("fireworks", models["providers"])
        install_script = (ROOT / "install.sh").read_text()
        picker = install_script.split("PICKER_ENABLED_MODELS = [", 1)[1].split("]", 1)[0]
        self.assertIn('"xai/grok-4.6:high"', picker)
        self.assertIn('"cursor/grok-4.6:high"', picker)
        self.assertIn('"synthetic/hf:moonshotai/Kimi-K3:high"', picker)
        self.assertNotIn("cursor/grok-4.5", picker)
        self.assertIn('"cursor/grok-4.5:high": "cursor/grok-4.6:high"', install_script)
        self.assertIn('"cursor/grok-4.6:fast": "cursor/grok-4.6"', install_script)
        self.assertIn('"cursor/grok-4.6:slow": "cursor/grok-4.6"', install_script)
        self.assertIn('fast_defaults["grok-4.6"] = False', install_script)
        for unscoped_model in (
            "fireworks/accounts/fireworks/models/deepseek-v4-flash-0731",
            "fireworks/accounts/fireworks/models/kimi-k3",
            "deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731",
            "deepinfra/zai-org/GLM-5.2",
        ):
            self.assertNotIn(unscoped_model, install_script)

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
        self.assertIn("decision-consistency", bodies["oracle"])
        self.assertIn("inherited decisions", bodies["oracle"])
        self.assertIn("do not edit", bodies["oracle"])
        self.assertIn("driving agent", bodies["oracle"])
        self.assertIn("recommendation", bodies["oracle"])
        self.assertIn("visual", bodies["imaging"])
        self.assertIn("read-only", bodies["imaging"])
        self.assertIn("do not guess", bodies["imaging"])
        self.assertIn("image path", bodies["imaging"])
        oracle_metadata, _ = frontmatter(AGENTS / "oracle.md")
        self.assertEqual("none", oracle_metadata.get("isolation"))
        self.assertEqual("true", oracle_metadata.get("inherit_context"))
        imaging_metadata, _ = frontmatter(AGENTS / "imaging.md")
        self.assertEqual("none", imaging_metadata.get("isolation"))
        self.assertNotIn("inherit_context", imaging_metadata)

    def test_oracle_is_proactively_available_inside_and_outside_workflows(self):
        doctrine = (ROOT / "APPEND_SYSTEM.md").read_text()
        self.assertIn("load `oracle-consultation`", doctrine)
        self.assertIn("invoke Oracle proactively", doctrine)
        self.assertIn("Do not wait for the operator to request it", doctrine)

        consultation = ROOT / "skills" / "oracle-consultation" / "SKILL.md"
        self.assertTrue(consultation.is_file())
        metadata, consultation_body = frontmatter(consultation)
        self.assertTrue(metadata["description"].startswith("Use when "))
        for required in (
            'subagent_type: "oracle"',
            "Do not use Oracle for routine",
            "current recommendation",
            "one narrow question",
            'Setting `inherit_context: false` or `isolation: "worktree"` is a workflow violation',
            "partially-accepted",
        ):
            self.assertIn(required, consultation_body)

        command = ROOT / "_pi" / "prompts" / "consult:oracle.md"
        self.assertTrue(command.is_file())
        command_text = command.read_text()
        self.assertIn("Load `oracle-consultation`", command_text)
        self.assertIn("verify", command_text.lower())

        oracle_body = frontmatter(AGENTS / "oracle.md")[1]
        self.assertIn("Caller contract", oracle_body)
        self.assertIn("workflow violation", oracle_body)
        self.assertIn("partially-accepted", oracle_body)

        workflow_surfaces = {
            ROOT / "skills" / "delivery-run" / "SKILL.md",
            ROOT / "skills" / "reviewed-html-plan" / "SKILL.md",
            ROOT / "skills" / "run-plan" / "SKILL.md",
            ROOT / "skills" / "autoreview" / "SKILL.md",
            ROOT / "_pi" / "prompts" / "dev:run.md",
            ROOT / "_pi" / "prompts" / "dev:reviewed-html-plan.md",
            ROOT / "_pi" / "prompts" / "delivery:run.md",
        }
        for path in workflow_surfaces:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn("oracle-consultation", path.read_text())

        self.assertTrue((ROOT / "scripts" / "probe_pi_oracle_transport.py").is_file())
        self.assertTrue((ROOT / "scripts" / "analyze_oracle_session.py").is_file())
        self.assertTrue((ROOT / "scripts" / "e2e_oracle_proactive_trigger.py").is_file())
        fixture_prompt = (
            ROOT / "scripts" / "fixtures" / "oracle-proactive-trigger" / "OPERATOR_PROMPT.md"
        ).read_text()
        self.assertNotRegex(fixture_prompt, r"(?i)\boracle\b")
        self.assertIn("decision-support workflow", fixture_prompt)

    def test_imaging_is_proactively_available_for_non_vision_models(self):
        doctrine = (ROOT / "APPEND_SYSTEM.md").read_text()
        self.assertIn("`imaging` subagent", doctrine)
        self.assertIn("cannot see an image", doctrine)
        self.assertIn("Do not wait for the operator to request it", doctrine)

        metadata, body = frontmatter(AGENTS / "imaging.md")
        self.assertIn("Use proactively", metadata.get("description", ""))
        self.assertIn("openai-codex/gpt-5.6-luna", metadata.get("model", ""))
        self.assertEqual("xhigh", metadata.get("thinking"))
        self.assertEqual("xhigh", metadata.get("reasoningEffort"))
        self.assertEqual("none", metadata.get("isolation"))
        self.assertIn("Caller contract", body)
        self.assertIn('subagent_type: "imaging"', body)
        self.assertIn("pi-clipboard-", body)
        self.assertIn("Need from driving agent", body)

        catalog = (ROOT / "AGENTS.md").read_text()
        self.assertIn("Exact Five-Agent Roster", catalog)
        self.assertIn("`imaging`", catalog)
        self.assertIn("Luna xhigh", catalog)

        readme = (ROOT / "_pi" / "README.md").read_text()
        self.assertIn("`imaging` — GPT-5.6 Luna xhigh", readme)

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

    def test_reviewer_never_refuses_visible_code_due_to_worktree_state(self):
        reviewer = (ROOT / "_pi" / "agents" / "reviewer.md").read_text()
        self.assertIn("Worktree state is provenance, never a reason to refuse a review", reviewer)
        self.assertIn("git -C <target>", reviewer)
        self.assertIn("REVIEW_ROOT", reviewer)
        self.assertIn("REVIEW_SOURCE", reviewer)

        review_surfaces = {
            ROOT / "skills" / "autoreview" / "SKILL.md": (
                "Use this prompt shape for each reviewer:",
                "Completion contract for every reviewer:",
            ),
            ROOT / "skills" / "run-plan" / "SKILL.md": (
                "## Reviewer Prompt Template",
                "For every reviewer slice, use bounded scope",
            ),
            ROOT / "skills" / "reviewed-html-plan" / "SKILL.md": (
                "#### Reviewer packet",
                "For the single plan-review pass",
            ),
        }
        retired_refusal_tokens = (
            "INSPECTED_TREE",
            "isolated-clean",
            "live-worktree launch contract",
            "discard it as `REVIEW_INFRASTRUCTURE_FAILURE`",
        )
        required_fields = (
            "TARGET_CHECKOUT",
            "COORDINATOR_HEAD",
            "COORDINATOR_STATUS_SHORT",
            "CWD",
            "REVIEW_ROOT",
            "HEAD",
            "STATUS_SHORT",
            "REVIEW_SOURCE",
        )
        for path, (start, end) in review_surfaces.items():
            text = path.read_text()
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertEqual(1, text.count(start), f"ambiguous start anchor: {start}")
                self.assertEqual(1, text.count(end), f"ambiguous end anchor: {end}")
                packet = text.split(start, 1)[1].split(end, 1)[0]
                for field in required_fields:
                    self.assertIn(field, packet)
                self.assertRegex(packet, r"(?is)changed.*untracked|untracked.*changed")
                for token in retired_refusal_tokens:
                    self.assertNotIn(token, text)

        for token in retired_refusal_tokens:
            self.assertNotIn(token, reviewer)

    def test_pi_review_launches_omit_worktree_isolation(self):
        for name in ("oracle", "reviewer", "planner", "imaging"):
            metadata, _ = frontmatter(ROOT / "_pi" / "agents" / f"{name}.md")
            self.assertEqual("none", metadata.get("isolation"))

        autoreview = (ROOT / "skills" / "autoreview" / "SKILL.md").read_text()
        self.assertIn("must omit the `isolation` property entirely", autoreview)
        self.assertIn("Never set `isolation: \"worktree\"`", autoreview)
        launch = autoreview.split("const review = Agent({", 1)[1].split("});", 1)[0]
        self.assertNotIn("isolation", launch)

        run_plan = (ROOT / "skills" / "run-plan" / "SKILL.md").read_text()
        self.assertIn("Every Pi `Agent` reviewer call must omit the `isolation` property entirely", run_plan)
        self.assertIn("requesting `isolation: \"worktree\"` is a workflow violation", run_plan)

        reviewed_plan = (ROOT / "skills" / "reviewed-html-plan" / "SKILL.md").read_text()
        self.assertIn("with the `isolation` property omitted entirely", reviewed_plan)
        self.assertIn("never set `isolation: \"worktree\"`", reviewed_plan)

        oracle_skill = (ROOT / "skills" / "oracle-consultation" / "SKILL.md").read_text()
        self.assertIn("Omit caller-side", oracle_skill)
        self.assertIn('isolation: "worktree"', oracle_skill)

        installer = (ROOT / "install.sh").read_text()
        self.assertIn("patch_pi_subagents_review_isolation.py", installer)
        review_stack = installer.split("install_pi_review_stack() {", 1)[1].split("remove_retired_pi_goal_plugin() {", 1)[0]
        patch_index = review_stack.index("patch_pi_subagents_review_isolation.py")
        first_mutation = review_stack.index('parent_metadata="$(mktemp)"')
        self.assertLess(patch_index, first_mutation)
        self.assertIn("preflight_pi_review_stack_contract false", review_stack[:patch_index])
        preflight = installer.split("preflight_pi_review_stack_contract() {", 1)[1].split("install_pi_review_stack() {", 1)[0]
        self.assertIn("probe_pi_review_transport.py", preflight)
        self.assertIn("pi-review-stack-managed-surfaces.json", review_stack)
        self.assertIn('"$contract" list', review_stack)
        self.assertGreaterEqual(installer.count("install_pi_review_stack full"), 3)
        self.assertNotIn("for skill in autoreview", review_stack)
        self.assertIn("return 1", review_stack[patch_index:first_mutation])
        readme = (ROOT / "_pi" / "README.md").read_text()
        self.assertIn("`oracle`, `planner`, and `reviewer` declare `isolation: none`", readme)

    def test_append_system_uses_progressive_disclosure(self):
        doctrine = (ROOT / "APPEND_SYSTEM.md").read_text()
        self.assertLess(len(doctrine.split()), 600)
        for skill in ("integration-integrity", "safe-git-index", "oracle-consultation"):
            self.assertIn(f"`{skill}`", doctrine)
        for moved_detail in (
            "ENSURE=",
            "openai-codex/gpt-5.6-sol",
            "Cursor Grok",
            "get_subagent_result",
            "TARGET_CHECKOUT",
        ):
            self.assertNotIn(moved_detail, doctrine)

        matrix = json.loads((ROOT / "skills" / "install-matrix.json").read_text())["installableSkills"]
        bodies = {}
        for skill in ("integration-integrity", "safe-git-index", "oracle-consultation"):
            path = ROOT / "skills" / skill / "SKILL.md"
            metadata, body = frontmatter(path)
            self.assertTrue(metadata["description"].startswith("Use when "), skill)
            self.assertLessEqual(len(metadata["description"].split()), 22, skill)
            self.assertIn(skill, matrix)
            bodies[skill] = body

        for required in ("After compaction, handoff, resume, rebase", "stale-reference search", "actual parser"):
            self.assertIn(required, bodies["integration-integrity"])
        for required in ("$HOME/.local/bin/git-with-index-lock", "$HOME/.agents/scripts/git-with-index-lock", "lsof", "Never silently fall back"):
            self.assertIn(required, bodies["safe-git-index"])

    def test_claude_has_only_the_read_only_reviewer_subagent(self):
        agents = ROOT / "_claude" / "agents"
        self.assertEqual({"reviewer.md"}, {path.name for path in agents.glob("*.md")})
        metadata, body = frontmatter(agents / "reviewer.md")
        self.assertEqual("reviewer", metadata.get("name"))
        self.assertEqual("claude-sonnet-5", metadata.get("model"))
        self.assertEqual("high", metadata.get("effort"))
        self.assertEqual("Read, Grep, Glob", metadata.get("tools"))
        self.assertIn("read-only", body.lower())
        self.assertIn("do not edit files", body.lower())
        self.assertIn("do not run tests", body.lower())

        installer = (ROOT / "install.sh").read_text()
        self.assertIn('rm -rf "$target/agents"', installer)
        self.assertIn('cp -r "$REPO_ROOT/_claude/agents" "$target/"', installer)

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
