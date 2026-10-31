// Fake of the paseo CLI's daemon client (dist/utils/client.js and dist/utils/daemon-target.js) for test_start_wks.py.
// `setWorkspacePinned` pins a workspace that exists in the fake paseo's state ($START_WKS_FAKE_STATE) by adding its
// id to `pins`. One-shot fault: `pin_fails` (the daemon rejects the request).
import { readFileSync, writeFileSync } from "node:fs";

const STATE = process.env.START_WKS_FAKE_STATE;

export function selectDaemonTarget() {
  return { kind: "instance" };
}

export async function connectToDaemon() {
  return {
    async setWorkspacePinned(workspaceId, pinned) {
      const state = JSON.parse(readFileSync(STATE, "utf8"));
      const fails = state.pin_fails;
      delete state.pin_fails;
      const known = state.workspaces.some((w) => w.workspaceId === workspaceId);
      if (!fails && known && pinned) state.pins = [...(state.pins ?? []), workspaceId];
      writeFileSync(STATE, JSON.stringify(state));
      if (fails) throw new Error("setWorkspacePinned rejected");
      if (!known) throw new Error("Workspace not found");
      return { pinnedAt: new Date().toISOString() };
    },
    async close() {},
  };
}
