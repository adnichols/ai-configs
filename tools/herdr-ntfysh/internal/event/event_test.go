package event

import (
	"os"
	"testing"
)

// clearRuntimeEnv unsets the HERDR_* runtime variables so tests exercising
// payload-only fallbacks are not perturbed by a herdr-hosted shell.
func clearRuntimeEnv(t *testing.T) {
	t.Helper()
	for _, k := range []string{"HERDR_WORKSPACE_ID", "HERDR_TAB_ID", "HERDR_PANE_ID"} {
		if _, ok := os.LookupEnv(k); ok {
			t.Setenv(k, "")
			os.Unsetenv(k)
		}
	}
}

const sample = `{
  "event": "pane.agent_status_changed",
  "data": {
    "agent_status": "Blocked",
    "display_agent": "Claude",
    "agent": "claude",
    "workspace": "api",
    "tab": "main",
    "pane_id": "w1:p2",
    "custom_status": "waiting for approval",
    "state_labels": {"error": "needs permission", "task": "refactor"}
  }
}`

func TestFromJSON(t *testing.T) {
	ev, err := FromJSON(sample)
	if err != nil {
		t.Fatal(err)
	}
	if ev.Name() != "pane.agent_status_changed" {
		t.Errorf("name = %q", ev.Name())
	}
	if ev.Status() != "blocked" {
		t.Errorf("status = %q, want lowercased blocked", ev.Status())
	}
	if ev.Agent() != "Claude" {
		t.Errorf("agent = %q, want display_agent Claude", ev.Agent())
	}
	if ev.Location() != "api › main" {
		t.Errorf("location = %q", ev.Location())
	}
	if ev.PaneKey() != "w1:p2" {
		t.Errorf("pane key = %q", ev.PaneKey())
	}
	if ev.ErrorLabel() != "needs permission" {
		t.Errorf("error label = %q", ev.ErrorLabel())
	}
}

func TestAgentFallback(t *testing.T) {
	ev, _ := FromJSON(`{"data":{"agent":"codex"}}`)
	if ev.Agent() != "codex" {
		t.Errorf("agent fallback = %q", ev.Agent())
	}
	empty, _ := FromJSON(`{"data":{}}`)
	if empty.Agent() != "agent" {
		t.Errorf("empty agent should default to 'agent', got %q", empty.Agent())
	}
}

func TestInvalidJSON(t *testing.T) {
	if _, err := FromJSON("not json"); err == nil {
		t.Error("expected parse error")
	}
}

func TestPaneKeyFallback(t *testing.T) {
	clearRuntimeEnv(t)
	// No pane_id, but workspace/tab present.
	ev, _ := FromJSON(`{"data":{"workspace":"api","tab":"main"}}`)
	if ev.PaneKey() != "api › main" {
		t.Errorf("pane key fallback = %q", ev.PaneKey())
	}
}
