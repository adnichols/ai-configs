package render

import (
	"strings"
	"testing"

	"github.com/cobanov/herdr-ntfysh/internal/config"
	"github.com/cobanov/herdr-ntfysh/internal/event"
)

func baseCfg() *config.Config {
	return &config.Config{
		Server:   "https://ntfy.example.com",
		Topic:    "herd",
		Priority: map[string]int{"done": 3, "blocked": 4, "working": 2, "idle": 2},
	}
}

func TestEventMessageDone(t *testing.T) {
	ev, _ := event.FromJSON(`{"data":{"agent_status":"idle","display_agent":"Claude","workspace_id":"api","tab_id":"main","state_labels":{"task":"tests green"}}}`)
	m := EventMessage(baseCfg(), ev, "done")

	if m.Title != "Claude - done" {
		t.Errorf("title = %q", m.Title)
	}
	if m.Priority != 3 {
		t.Errorf("priority = %d, want 3", m.Priority)
	}
	if len(m.Tags) == 0 || m.Tags[0] != "white_check_mark" {
		t.Errorf("tags = %v, want white_check_mark first", m.Tags)
	}
	if !strings.Contains(m.Body, "tests green") {
		t.Errorf("body should use task label: %q", m.Body)
	}
	if !strings.Contains(m.Body, "api › main") {
		t.Errorf("body should include location: %q", m.Body)
	}
}

func TestEventMessageBlocked(t *testing.T) {
	ev, _ := event.FromJSON(`{"data":{"agent_status":"blocked","display_agent":"Codex","state_labels":{"error":"needs your approval"}}}`)
	m := EventMessage(baseCfg(), ev, "blocked")

	if m.Title != "Codex - needs input" {
		t.Errorf("title = %q", m.Title)
	}
	if m.Priority != 4 {
		t.Errorf("priority = %d, want 4", m.Priority)
	}
	if m.Tags[0] != "rotating_light" {
		t.Errorf("tags = %v, want rotating_light first", m.Tags)
	}
	if !strings.Contains(m.Body, "needs your approval") {
		t.Errorf("body should use error label: %q", m.Body)
	}
}

func TestTitlePrefixAndExtraTags(t *testing.T) {
	cfg := baseCfg()
	cfg.TitlePrefix = "[herdr]"
	cfg.TagsExtra = []string{"computer"}
	ev, _ := event.FromJSON(`{"data":{"agent_status":"idle","display_agent":"Claude"}}`)
	m := EventMessage(cfg, ev, "done")

	if !strings.HasPrefix(m.Title, "[herdr] ") {
		t.Errorf("title prefix missing: %q", m.Title)
	}
	if m.Tags[len(m.Tags)-1] != "computer" {
		t.Errorf("extra tag missing: %v", m.Tags)
	}
}

func TestFallbackDetail(t *testing.T) {
	// No labels, no custom status -> generic sentence per status.
	ev, _ := event.FromJSON(`{"data":{"agent_status":"idle","display_agent":"Claude"}}`)
	m := EventMessage(baseCfg(), ev, "done")
	if !strings.Contains(m.Body, "finished its task") {
		t.Errorf("expected generic done detail: %q", m.Body)
	}
}

func TestTestMessage(t *testing.T) {
	m := TestMessage(baseCfg())
	if !strings.Contains(m.Title, "test") {
		t.Errorf("test title = %q", m.Title)
	}
	if !strings.Contains(m.Body, "ntfy.example.com/herd") {
		t.Errorf("test body should reference server/topic: %q", m.Body)
	}
}
