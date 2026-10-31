// Pin a Paseo workspace to the sidebar: pin_workspace.mjs <workspace-id>
//
// The paseo CLI (0.13, 0.14) has no pin command. This sends the request the app's pin button sends
// (`setWorkspacePinned`) through the CLI's own daemon client, loaded from $PASEO_CLI_DIST, so it reaches the same
// daemon, with the same credentials, as `paseo` does. Prints {"pinnedAt": ...}; exits 1 with the daemon's error.
import { pathToFileURL } from "node:url";

const dist = process.env.PASEO_CLI_DIST;
const workspaceId = process.argv.at(-1);
try {
  const { connectToDaemon } = await import(pathToFileURL(`${dist}/utils/client.js`).href);
  const { selectDaemonTarget } = await import(pathToFileURL(`${dist}/utils/daemon-target.js`).href);
  const client = await connectToDaemon({ target: selectDaemonTarget({}) });
  try {
    console.log(JSON.stringify(await client.setWorkspacePinned(workspaceId, true)));
  } finally {
    await client.close().catch(() => undefined);
  }
} catch (error) {
  console.error(`pin ${workspaceId}: ${error?.message ?? error}`);
  process.exit(1);
}
