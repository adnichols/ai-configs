#!/usr/bin/env python3
"""Contract tests for vendored pi-prewalk profiles and package layout."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "_pi" / "packages" / "pi-prewalk"
PROFILES = PKG / "profiles.json"
EXTENSION = PKG / "extensions" / "prewalk.ts"
PACKAGE_JSON = PKG / "package.json"


class PiPrewalkProfilesTest(unittest.TestCase):
    def test_package_layout(self) -> None:
        self.assertTrue(PKG.is_dir())
        self.assertTrue(PROFILES.is_file())
        self.assertTrue(EXTENSION.is_file())
        self.assertTrue(PACKAGE_JSON.is_file())
        self.assertTrue((PKG / "LICENSE").is_file())
        self.assertTrue((PKG / "README.md").is_file())
        meta = json.loads(PACKAGE_JSON.read_text())
        self.assertEqual("@adnichols/pi-prewalk", meta.get("name"))
        self.assertEqual(["./extensions"], meta.get("pi", {}).get("extensions"))

    def test_default_profiles_cover_flash_terra_glm_luna(self) -> None:
        cfg = json.loads(PROFILES.read_text())
        self.assertEqual("flash", cfg.get("defaultProfile"))
        profiles = cfg.get("profiles") or {}
        for name in ("flash", "terra", "glm", "luna"):
            self.assertIn(name, profiles, name)
            entry = profiles[name]
            self.assertTrue(entry.get("provider"), name)
            self.assertTrue(entry.get("id"), name)
            self.assertIn(
                entry.get("thinkingLevel"),
                {"off", "minimal", "low", "medium", "high", "xhigh", "max"},
                name,
            )
        self.assertNotIn("sol", profiles)
        flash = profiles["flash"]
        self.assertEqual("deepinfra", flash["provider"])
        self.assertEqual("deepseek-ai/DeepSeek-V4-Flash-0731", flash["id"])
        glm = profiles["glm"]
        self.assertEqual("deepinfra", glm["provider"])
        self.assertEqual("zai-org/GLM-5.2", glm["id"])
        self.assertEqual("high", glm["thinkingLevel"])

    def test_extension_exports_profile_helpers_and_commands(self) -> None:
        source = EXTENSION.read_text()
        for needle in (
            "mergePrewalkConfigs",
            "loadPrewalkConfig",
            "parseTargetSpec",
            "prewalk-profiles.json",
            'registerCommand("prewalk"',
            "profiles",
            "default ",
            "sessionDefaultProfile",
        ):
            self.assertIn(needle, source)

    def test_install_sh_vendors_prewalk_not_npm(self) -> None:
        install = (ROOT / "install.sh").read_text()
        self.assertIn("install_vendored_pi_prewalk", install)
        self.assertIn('_pi/packages/pi-prewalk', install)
        # npm list should not install pi-prewalk; deprecated list should.
        npm_block = install.split("local npm_packages=(", 1)[1].split(")", 1)[0]
        self.assertNotIn('"pi-prewalk"', npm_block)
        deprecated_block = install.split("local deprecated_npm_packages=(", 1)[1].split(")", 1)[0]
        self.assertIn('"pi-prewalk"', deprecated_block)
        self.assertNotIn("patch_pi_prewalk_execution_target.py", install)

    def test_merge_logic_via_node(self) -> None:
        """Exercise exported merge/parse helpers when Node can load the TS module."""
        script = r"""
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

async function main() {
  const root = process.argv[1];
  const ext = path.join(root, "_pi/packages/pi-prewalk/extensions/prewalk.ts");
  let mod;
  try {
    const jitiPath = require.resolve("jiti", {
      paths: [
        path.join(process.env.HOME || "", ".pi/agent/npm/node_modules"),
        path.join(root, "node_modules"),
      ],
    });
    const jiti = require(jitiPath);
    const load = jiti(__filename, { interopDefault: true });
    mod = load(ext);
  } catch (err) {
    // Fall back: dynamic import may work on newer Node with type stripping.
    try {
      mod = await import(pathToFileURL(ext).href);
    } catch (err2) {
      console.log("SKIP:" + String(err2 && err2.message ? err2.message : err2));
      process.exit(0);
    }
  }
  const { mergePrewalkConfigs, parseTargetSpec } = mod;
  if (typeof mergePrewalkConfigs !== "function" || typeof parseTargetSpec !== "function") {
    throw new Error("expected mergePrewalkConfigs and parseTargetSpec exports");
  }
  const pkg = JSON.parse(fs.readFileSync(path.join(root, "_pi/packages/pi-prewalk/profiles.json"), "utf8"));
  const merged = mergePrewalkConfigs(pkg, {
    defaultProfile: "terra",
    profiles: {
      cheap: {
        provider: "deepinfra",
        id: "deepseek-ai/DeepSeek-V4-Flash-0731",
        thinkingLevel: "minimal",
      },
      terra: { thinkingLevel: "xhigh" },
    },
  });
  if (merged.defaultProfile !== "terra") throw new Error("defaultProfile override failed");
  if (!merged.profiles.flash) throw new Error("package flash profile missing");
  if (!merged.profiles.cheap || merged.profiles.cheap.thinkingLevel !== "minimal") {
    throw new Error("user profile not merged");
  }
  if (merged.profiles.terra.thinkingLevel !== "xhigh") throw new Error("profile overlay failed");
  if (merged.profiles.terra.provider !== "openai-codex") throw new Error("overlay dropped provider");
  const parsed = parseTargetSpec("flash:high");
  if (parsed.modelSpec !== "flash" || parsed.thinkingLevel !== "high") {
    throw new Error("parseTargetSpec failed: " + JSON.stringify(parsed));
  }
  console.log("OK");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
"""
        proc = subprocess.run(
            ["node", "-e", script, str(ROOT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if "SKIP:" in out:
            self.skipTest(f"node could not load prewalk.ts: {out.strip()}")
        self.assertEqual(0, proc.returncode, out)
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
