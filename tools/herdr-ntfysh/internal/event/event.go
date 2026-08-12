// Package event parses the herdr event payload delivered through
// HERDR_PLUGIN_EVENT_JSON and exposes it via accessors that fall back to the
// standard HERDR_* runtime variables when a field is absent.
//
// The payload shape follows the pane.agent_status_changed event: a top-level
// object with an "event" name and a "data" object carrying the agent status
// and location. All fields are treated as optional — herdr versions differ,
// so we degrade gracefully rather than assume a rigid schema.
package event

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type stateLabels struct {
	Error string `json:"error"`
	Task  string `json:"task"`
}

type data struct {
	AgentStatus  string      `json:"agent_status"`
	Agent        string      `json:"agent"`
	DisplayAgent string      `json:"display_agent"`
	Workspace    string      `json:"workspace"`
	WorkspaceID  string      `json:"workspace_id"`
	Tab          string      `json:"tab"`
	TabID        string      `json:"tab_id"`
	PaneID       string      `json:"pane_id"`
	CustomStatus string      `json:"custom_status"`
	Title        string      `json:"title"`
	StateLabels  stateLabels `json:"state_labels"`
}

type payload struct {
	Event string `json:"event"`
	Data  data   `json:"data"`
}

// Event is a parsed herdr event.
type Event struct {
	p payload
}

// FromEnv reads and parses HERDR_PLUGIN_EVENT_JSON.
func FromEnv() (*Event, error) {
	raw := os.Getenv("HERDR_PLUGIN_EVENT_JSON")
	if strings.TrimSpace(raw) == "" {
		return nil, errors.New("HERDR_PLUGIN_EVENT_JSON is not set")
	}
	return FromJSON(raw)
}

// FromJSON parses a raw event JSON string.
func FromJSON(raw string) (*Event, error) {
	var p payload
	if err := json.Unmarshal([]byte(raw), &p); err != nil {
		return nil, fmt.Errorf("parse event json: %w", err)
	}
	return &Event{p: p}, nil
}

// Name is the herdr event name (e.g. "pane.agent_status_changed").
func (e *Event) Name() string { return e.p.Event }

// Status is the lower-cased agent status (done, blocked, working, idle).
func (e *Event) Status() string {
	return strings.ToLower(strings.TrimSpace(e.p.Data.AgentStatus))
}

// Agent returns the friendliest available agent name.
func (e *Event) Agent() string {
	return firstNonEmpty(e.p.Data.DisplayAgent, e.p.Data.Agent, "agent")
}

// Workspace prefers the payload's workspace/workspace_id, then the
// HERDR_WORKSPACE_ID runtime variable.
func (e *Event) Workspace() string {
	return firstNonEmpty(e.p.Data.Workspace, e.p.Data.WorkspaceID, os.Getenv("HERDR_WORKSPACE_ID"))
}

// Tab prefers the payload's tab/tab_id, then the HERDR_TAB_ID runtime variable.
func (e *Event) Tab() string {
	return firstNonEmpty(e.p.Data.Tab, e.p.Data.TabID, os.Getenv("HERDR_TAB_ID"))
}

// PaneID falls back to the HERDR_PANE_ID runtime variable.
func (e *Event) PaneID() string {
	return firstNonEmpty(e.p.Data.PaneID, os.Getenv("HERDR_PANE_ID"))
}

// CustomStatus is the agent's free-form status text, if any.
func (e *Event) CustomStatus() string { return strings.TrimSpace(e.p.Data.CustomStatus) }

// SessionTitle asks the running herdr for the agent's human-readable session
// title, preferring the agent rename name over the pane terminal title. It
// returns "" (and callers fall back to the event fields) when herdr is
// unreachable or the agent has neither.
func (e *Event) SessionTitle() string {
	pane := e.PaneID()
	if pane == "" {
		return ""
	}
	info, err := herdrJSON("agent", "get", pane)
	if err != nil {
		return ""
	}
	result, _ := info["result"].(map[string]any)
	agent, _ := result["agent"].(map[string]any)
	for _, key := range []string{"name", "terminal_title"} {
		if s, _ := agent[key].(string); strings.TrimSpace(s) != "" {
			return s
		}
	}
	return ""
}

// RecentOutput returns the last n lines of the pane's recent scrollback (the
// agent's latest output). Empty when herdr is unreachable or n <= 0.
func (e *Event) RecentOutput(n int) string {
	if n <= 0 {
		return ""
	}
	pane := e.PaneID()
	if pane == "" {
		return ""
	}
	return herdrText("pane", "read", pane, "--source", "recent-unwrapped", "--lines", strconv.Itoa(n))
}

func herdrBin() string {
	if b := os.Getenv("HERDR_BIN_PATH"); b != "" {
		return b
	}
	return "herdr"
}

// herdrJSON runs a read-only herdr CLI call expecting a JSON response.
func herdrJSON(args ...string) (map[string]any, error) {
	out, err := herdrOutput(args...)
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := json.Unmarshal(out, &m); err != nil {
		return nil, err
	}
	return m, nil
}

// herdrText runs a read-only herdr CLI call expecting plain-text output.
func herdrText(args ...string) string {
	out, err := herdrOutput(args...)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

// herdrOutput runs a read-only herdr CLI call with a bounded timeout so a
// stalled socket never stalls herdr's event pipeline.
func herdrOutput(args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return exec.CommandContext(ctx, herdrBin(), args...).Output()
}

// TaskLabel is the state_labels.task hint (typically set for done/working).
func (e *Event) TaskLabel() string { return strings.TrimSpace(e.p.Data.StateLabels.Task) }

// ErrorLabel is the state_labels.error hint (typically set for blocked).
func (e *Event) ErrorLabel() string { return strings.TrimSpace(e.p.Data.StateLabels.Error) }

// Location renders a human-readable "workspace › tab" breadcrumb, omitting
// empty segments.
func (e *Event) Location() string {
	var parts []string
	if ws := e.Workspace(); ws != "" {
		parts = append(parts, ws)
	}
	if tab := e.Tab(); tab != "" {
		parts = append(parts, tab)
	}
	return strings.Join(parts, " › ")
}

// PaneKey is a stable identifier for debounce bookkeeping. It prefers the
// pane id and falls back to the workspace/tab pair.
func (e *Event) PaneKey() string {
	if id := e.PaneID(); id != "" {
		return id
	}
	if loc := e.Location(); loc != "" {
		return loc
	}
	return "unknown"
}

func firstNonEmpty(vals ...string) string {
	for _, v := range vals {
		if s := strings.TrimSpace(v); s != "" {
			return s
		}
	}
	return ""
}
