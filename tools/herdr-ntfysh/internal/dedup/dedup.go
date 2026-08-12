// Package dedup persists per-pane state across the short-lived plugin
// invocations herdr spawns. It serves two jobs:
//
//   - Transition tracking: remember the last status seen for a pane so the
//     next event can tell working->idle ("done") apart from a plain idle.
//   - Debounce: suppress a repeat notification of the same kind for the same
//     pane within a time window, so a flapping agent can't spam pushes.
//
// State is a small JSON map under HERDR_PLUGIN_STATE_DIR (the durable
// per-plugin location herdr provides). Without a state dir there is no memory
// between invocations, so transitions cannot be detected and debouncing is
// off; callers should treat that as best-effort.
package dedup

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"github.com/cobanov/herdr-ntfysh/internal/config"
)

const stateFile = "panes.json"

type entry struct {
	// Status is the last status seen for the pane.
	Status   string `json:"status"`
	StatusTs int64  `json:"status_ts"`
	// Notify is the kind of the last notification sent for the pane.
	Notify   string `json:"notify"`
	NotifyTs int64  `json:"notify_ts"`
}

// Store is the persisted per-pane state for the current run.
type Store struct {
	path    string
	window  int64
	data    map[string]entry
	enabled bool
	dirty   bool
	now     func() int64
}

// Open loads existing state for the current run.
func Open(cfg *config.Config) *Store {
	s := &Store{
		data:    map[string]entry{},
		window:  int64(cfg.DedupWindow),
		enabled: cfg.StateDir != "",
		now:     func() int64 { return time.Now().Unix() },
	}
	if !s.enabled {
		return s
	}
	s.path = filepath.Join(cfg.StateDir, stateFile)
	if b, err := os.ReadFile(s.path); err == nil {
		_ = json.Unmarshal(b, &s.data) // corrupt state is treated as empty
	}
	return s
}

// Prev returns the last status seen for a pane, or "" if unknown.
func (s *Store) Prev(key string) string {
	return s.data[key].Status
}

// RecordSeen updates the last-seen status for a pane. It should be called for
// every event, notified or not, so transition detection stays accurate.
func (s *Store) RecordSeen(key, status string) {
	e := s.data[key]
	e.Status = status
	e.StatusTs = s.now()
	s.data[key] = e
	s.dirty = true
}

// AllowNotify reports whether a notification of kind may be sent for a pane,
// i.e. the same kind was not already sent within the debounce window.
func (s *Store) AllowNotify(key, kind string) bool {
	if s.window <= 0 {
		return true
	}
	e := s.data[key]
	if e.Notify == kind && s.now()-e.NotifyTs < s.window {
		return false
	}
	return true
}

// RecordNotify records that a notification of kind was just sent for a pane.
func (s *Store) RecordNotify(key, kind string) {
	e := s.data[key]
	e.Notify = kind
	e.NotifyTs = s.now()
	s.data[key] = e
	s.dirty = true
}

// Persist writes state to disk if anything changed. It is a no-op when
// disabled or unchanged.
func (s *Store) Persist() {
	if !s.enabled || !s.dirty {
		return
	}
	b, err := json.Marshal(s.data)
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(s.path), 0o755); err != nil {
		return
	}
	// Write-then-rename so a crash never leaves a truncated state file.
	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, b, 0o644); err != nil {
		return
	}
	_ = os.Rename(tmp, s.path)
}
