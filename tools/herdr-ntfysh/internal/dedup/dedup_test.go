package dedup

import (
	"testing"

	"github.com/cobanov/herdr-ntfysh/internal/config"
)

func newStore(t *testing.T, window int) (*Store, *int64) {
	t.Helper()
	cfg := &config.Config{StateDir: t.TempDir(), DedupWindow: window}
	s := Open(cfg)
	var clock int64 = 1000
	s.now = func() int64 { return clock }
	return s, &clock
}

func TestPrevTracksLastSeen(t *testing.T) {
	s, _ := newStore(t, 10)
	if s.Prev("p1") != "" {
		t.Error("unknown pane should have empty prev")
	}
	s.RecordSeen("p1", "working")
	if s.Prev("p1") != "working" {
		t.Errorf("prev = %q, want working", s.Prev("p1"))
	}
	s.RecordSeen("p1", "idle")
	if s.Prev("p1") != "idle" {
		t.Errorf("prev = %q, want idle", s.Prev("p1"))
	}
}

func TestDebounceSuppressesSameKind(t *testing.T) {
	s, clock := newStore(t, 10)

	if !s.AllowNotify("p1", "done") {
		t.Fatal("first notification should be allowed")
	}
	s.RecordNotify("p1", "done")

	*clock = 1005 // within window
	if s.AllowNotify("p1", "done") {
		t.Error("repeat same kind within window should be suppressed")
	}

	*clock = 1011 // past window
	if !s.AllowNotify("p1", "done") {
		t.Error("after window, notification should be allowed again")
	}
}

func TestDifferentKindNotSuppressed(t *testing.T) {
	s, _ := newStore(t, 10)
	s.RecordNotify("p1", "done")
	if !s.AllowNotify("p1", "blocked") {
		t.Error("different kind should not be suppressed")
	}
}

func TestSeenAndNotifyAreIndependent(t *testing.T) {
	// Recording a sighting must not reset debounce bookkeeping.
	s, clock := newStore(t, 10)
	s.RecordNotify("p1", "done")
	*clock = 1003
	s.RecordSeen("p1", "working")
	if s.AllowNotify("p1", "done") {
		t.Error("recording a sighting should not clear the debounce window")
	}
}

func TestPersistenceAcrossOpens(t *testing.T) {
	dir := t.TempDir()
	cfg := &config.Config{StateDir: dir, DedupWindow: 10}

	s1 := Open(cfg)
	s1.now = func() int64 { return 1000 }
	s1.RecordSeen("p1", "working")
	s1.RecordNotify("p1", "done")
	s1.Persist()

	// A fresh process/run should load the persisted state.
	s2 := Open(cfg)
	s2.now = func() int64 { return 1005 }
	if s2.Prev("p1") != "working" {
		t.Errorf("persisted last-seen not loaded: %q", s2.Prev("p1"))
	}
	if s2.AllowNotify("p1", "done") {
		t.Error("persisted debounce state not loaded across Open calls")
	}
}

func TestDisabledWhenNoStateDir(t *testing.T) {
	s := Open(&config.Config{StateDir: "", DedupWindow: 10})
	s.RecordSeen("p1", "working")
	s.RecordNotify("p1", "done")
	// Nothing persists, but in-memory behavior stays sane within a run.
	if !s.AllowNotify("p2", "done") {
		t.Error("unrelated pane should be allowed")
	}
	s.Persist() // must not panic
}
