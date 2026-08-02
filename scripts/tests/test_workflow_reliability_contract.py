import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class WorkflowReliabilityContractTest(unittest.TestCase):
    def test_run_plan_bounds_strict_failures_scratch_and_final_candidate(self):
        canonical = (ROOT / "skills/run-plan/SKILL.md").read_text()
        for phrase in (
            "predecessor/upgrade compatibility",
            "exactly one bounded no-fail-fast inventory pass per delivery head",
            "Cap detailed distinct signatures at five",
            "requires the same signature reproduced at `git merge-base <base> HEAD`",
            "ownership marker with run ID",
            "report file count and bytes plus owner/lock diagnostics",
            'git diff --check "$MERGE_BASE"..HEAD',
            "registered Doct source/version reflects the current plan",
            "PR #TBD",
            "TODO-PR",
            "CHANGELOG_PLACEHOLDER",
        ):
            self.assertIn(phrase, canonical)
        hermes = (ROOT / "_hermes/default/skills/software-development/run-plan/SKILL.md").read_text()
        for phrase in ("predecessor/upgrade", "no-fail-fast inventory", "marked run-owned scratch roots", "PR #TBD", "CHANGELOG_PLACEHOLDER"):
            self.assertIn(phrase, hermes)

    def test_pr_and_fixture_guidance_use_committed_range_and_explicit_axes(self):
        create_pr = (ROOT / "skills/cmd-create-pr/SKILL.md").read_text()
        self.assertIn('git diff --check "$MERGE_BASE"..HEAD', create_pr)
        self.assertIn("incomplete plan progress", create_pr)
        fixture = (ROOT / "skills/tdd-test-writer/SKILL.md").read_text()
        self.assertIn("Hub availability/default state", fixture)
        self.assertIn("selected profile or account root", fixture)
        self.assertIn("Missing axes are fixture setup failures", fixture)

    def test_every_ledger_writer_is_classified_and_reaches_locked_write_json(self):
        source = (ROOT / "skills/delivery-run/scripts/delivery").read_text()
        tree = ast.parse(source)
        commands = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        read_only = {"path", "show", "verify-implementation-profile", "check", "board", "status", "stages"}
        writers = {"init", "stage", "approve-implementation", "start-implementation", "revoke-implementation-approval", "note", "set", "record", "record-receipt", "completion-review", "blocker", "reflect", "spawn", "bootstrap"}
        self.assertEqual(commands, read_only | writers)

        functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        calls = {
            name: {call.func.id for call in ast.walk(node) if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)}
            for name, node in functions.items()
        }
        writer_functions = {
            "cmd_init", "cmd_stage", "cmd_approve_implementation", "cmd_start_implementation",
            "cmd_revoke_implementation_approval", "cmd_note", "cmd_set", "cmd_record",
            "cmd_record_receipt", "cmd_completion_review", "cmd_blocker", "cmd_reflect", "cmd_spawn", "cmd_bootstrap",
        }

        def reaches_locked_writer(name):
            pending, seen = [name], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                if "write_json" in calls.get(current, set()):
                    return True
                pending.extend(calls.get(current, set()) & functions.keys())
            return False

        for name in writer_functions:
            self.assertIn(name, functions)
            self.assertTrue(reaches_locked_writer(name), name)
        self.assertNotIn("json.dump(", source)
        self.assertEqual(1, source.count("os.replace(tmp, path)"))

    def test_delivery_uses_current_herdr_json_default_without_removed_flag(self):
        delivery = (ROOT / "skills/delivery-run/scripts/delivery").read_text()
        self.assertIn("proc = run_cmd([herdr, *args], cwd=cwd)", delivery)
        self.assertNotIn('proc = run_cmd([herdr, *args, "--json"]', delivery)

    def test_full_and_bounded_pi_routes_reconcile_from_manifest(self):
        installer = (ROOT / "install.sh").read_text()
        self.assertIn('local manifest_scope="${1:-pi-review-stack}"', installer)
        preflight = installer.index('case "$INSTALL_MODE" in\n    --default|--pi|--all) preflight_pi_review_stack_contract true')
        first_full_mutation = installer.index('cleanup_retired_runtime_surfaces "$TARGET_DIR"', preflight)
        self.assertLess(preflight, first_full_mutation)
        self.assertIn('npm install --prefix "$preflight_agent/npm"', installer)
        self.assertNotIn("transport package absent before full-install bootstrap", installer)
        self.assertGreaterEqual(installer.count("install_pi_review_stack full"), 3)
        self.assertIn('--scope "$manifest_scope"', installer)
        self.assertIn('"$contract" verify', installer)


if __name__ == "__main__":
    unittest.main()
