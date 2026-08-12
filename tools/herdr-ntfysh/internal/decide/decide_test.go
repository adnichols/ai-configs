package decide

import (
	"testing"

	"github.com/cobanov/herdr-ntfysh/internal/config"
)

func cfg(on ...string) *config.Config {
	set := map[string]bool{}
	for _, s := range on {
		set[s] = true
	}
	return &config.Config{NotifyOn: set}
}

func TestExplicitDone(t *testing.T) {
	// herdr often emits "done" directly on completion.
	for _, prev := range []string{"", "working", "idle"} {
		d := Decide(cfg("done", "blocked"), prev, "done")
		if !d.Notify || d.Kind != "done" {
			t.Errorf("explicit done (prev=%q) should notify done, got %+v", prev, d)
		}
	}
}

func TestWorkingToIdleIsDone(t *testing.T) {
	d := Decide(cfg("done", "blocked"), "working", "idle")
	if !d.Notify || d.Kind != "done" {
		t.Errorf("working->idle should be done, got %+v", d)
	}
}

func TestIdleWithoutPriorWorkingIsSilent(t *testing.T) {
	// A plain idle (e.g. unknown->idle, or first sighting) is not "done".
	if d := Decide(cfg("done", "blocked"), "", "idle"); d.Notify {
		t.Errorf("idle without prior working should be silent, got %+v", d)
	}
	if d := Decide(cfg("done", "blocked"), "idle", "idle"); d.Notify {
		t.Errorf("idle->idle should be silent, got %+v", d)
	}
}

func TestBlocked(t *testing.T) {
	if d := Decide(cfg("done", "blocked"), "working", "blocked"); !d.Notify || d.Kind != "blocked" {
		t.Errorf("entering blocked should notify, got %+v", d)
	}
	// Re-emitted blocked should not re-notify.
	if d := Decide(cfg("done", "blocked"), "blocked", "blocked"); d.Notify {
		t.Errorf("repeated blocked should be silent, got %+v", d)
	}
}

func TestNotConfigured(t *testing.T) {
	// Only blocked enabled: a working->idle done must stay silent.
	if d := Decide(cfg("blocked"), "working", "idle"); d.Notify {
		t.Errorf("done disabled should be silent, got %+v", d)
	}
}

func TestOptInRawIdleAndWorking(t *testing.T) {
	if d := Decide(cfg("idle"), "blocked", "idle"); !d.Notify || d.Kind != "idle" {
		t.Errorf("raw idle opt-in should notify, got %+v", d)
	}
	if d := Decide(cfg("working"), "idle", "working"); !d.Notify || d.Kind != "working" {
		t.Errorf("working opt-in should notify, got %+v", d)
	}
}

func TestDonePrefersOverRawIdle(t *testing.T) {
	// With both done and idle enabled, working->idle should read as done.
	if d := Decide(cfg("done", "idle"), "working", "idle"); d.Kind != "done" {
		t.Errorf("working->idle should prefer done, got %+v", d)
	}
}
