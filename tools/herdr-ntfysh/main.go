// Command herdr-ntfysh is a herdr plugin that publishes ntfy notifications
// when a herdr-managed agent changes state (e.g. finishes work or blocks
// waiting for your input).
//
// herdr invokes this binary in two ways:
//
//   - As an event hook on "pane.agent_status_changed". herdr sets
//     HERDR_PLUGIN_EVENT_JSON and the standard plugin runtime variables, and
//     we decide whether the status warrants a push.
//   - As an action ("--test", "--doctor") the user triggers manually to
//     verify their configuration.
//
// The design goal is to be invisible when it works and safe when it doesn't:
// any misconfiguration or ntfy outage is logged to stderr (captured by
// `herdr plugin log list`) and the process exits 0 so the herdr event
// pipeline is never disrupted. Only the user-facing --test/--doctor actions
// exit non-zero on failure.
package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/cobanov/herdr-ntfysh/internal/config"
	"github.com/cobanov/herdr-ntfysh/internal/decide"
	"github.com/cobanov/herdr-ntfysh/internal/dedup"
	"github.com/cobanov/herdr-ntfysh/internal/event"
	"github.com/cobanov/herdr-ntfysh/internal/ntfy"
	"github.com/cobanov/herdr-ntfysh/internal/render"
)

const version = "0.2.1"

// logf writes a diagnostic line to stderr. herdr captures plugin stderr and
// exposes it via `herdr plugin log list --plugin cobanov.herdr-ntfysh`.
func logf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "herdr-ntfysh: "+format+"\n", args...)
}

// headLine returns the first non-empty line, capped for log readability.
func headLine(s string) string {
	const max = 120
	for _, line := range strings.SplitN(s, "\n", 2) {
		line = strings.TrimSpace(line)
		if line != "" {
			if len(line) > max {
				return line[:max] + "…"
			}
			return line
		}
	}
	return ""
}

func main() {
	os.Exit(run())
}

func run() int {
	var (
		testMode   bool
		doctorMode bool
		showVer    bool
	)
	flag.BoolVar(&testMode, "test", false, "send a test notification and exit")
	flag.BoolVar(&doctorMode, "doctor", false, "print resolved configuration (secrets redacted) and exit")
	flag.BoolVar(&showVer, "version", false, "print version and exit")
	flag.Parse()

	if showVer {
		fmt.Println("herdr-ntfysh", version)
		return 0
	}

	// Whether a failure should be surfaced to the user (exit non-zero) or
	// swallowed to protect herdr's event pipeline.
	userFacing := testMode || doctorMode

	cfg, err := config.Load()
	if err != nil {
		logf("config error: %v", err)
		if userFacing {
			return 1
		}
		return 0
	}

	if doctorMode {
		cfg.PrintRedacted(os.Stdout)
		return 0
	}

	if !cfg.Enabled {
		logf("disabled (HERDR_NTFY_ENABLED=false), skipping")
		return 0
	}

	client := ntfy.New(cfg)

	if testMode {
		if err := client.Publish(render.TestMessage(cfg)); err != nil {
			logf("test notification failed: %v", err)
			return 1
		}
		fmt.Printf("herdr-ntfysh: test notification sent to %s/%s\n", cfg.Server, cfg.Topic)
		return 0
	}

	// Event mode: triggered by herdr on pane.agent_status_changed.
	ev, err := event.FromEnv()
	if err != nil {
		logf("cannot read event: %v", err)
		return 0
	}

	status := ev.Status()
	if status == "" {
		logf("event carried no agent status, skipping")
		return 0
	}

	// State persists across invocations: it lets us tell a working->idle
	// "done" apart from a plain idle, and debounce repeat notifications.
	store := dedup.Open(cfg)
	key := ev.PaneKey()
	prev := store.Prev(key)

	// herdr never emits a "done" status; decide derives it from the
	// prev->cur transition. Record the sighting either way.
	dec := decide.Decide(cfg, prev, status)
	store.RecordSeen(key, status)
	defer store.Persist()

	if cfg.Debug {
		logf("DEBUG raw event: %s", os.Getenv("HERDR_PLUGIN_EVENT_JSON"))
		logf("DEBUG %s: prev=%q cur=%q -> notify=%t kind=%q", key, prev, status, dec.Notify, dec.Kind)
	}

	if !dec.Notify {
		return 0
	}
	if !store.AllowNotify(key, dec.Kind) {
		logf("debounced %q for %s", dec.Kind, key)
		return 0
	}

	msg := render.EventMessage(cfg, ev, dec.Kind)
	if cfg.Debug {
		logf("DEBUG notify title=%q body_bytes=%d body_head=%q", msg.Title, len(msg.Body), headLine(msg.Body))
	}
	if err := client.Publish(msg); err != nil {
		// A transient ntfy outage must not break herdr; log and move on.
		logf("publish failed: %v", err)
		return 0
	}
	store.RecordNotify(key, dec.Kind)
	logf("notified %q for %s", dec.Kind, key)
	return 0
}
