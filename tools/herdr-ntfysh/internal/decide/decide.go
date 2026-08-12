// Package decide maps a herdr agent-status transition to a notification
// decision.
//
// herdr rolls a pane up to one of idle | working | blocked | done | unknown.
// Empirically it emits "done" directly when a turn finishes, but some
// completions surface as a plain working -> idle transition instead. To catch
// both, "done" is triggered by either an explicit "done" status or a
// working -> idle transition:
//
//	done            -> notify (kind "done")     explicit completion
//	working -> idle -> notify (kind "done")     completion seen as idle
//	blocked         -> notify (kind "blocked")  on entering blocked
//	-> working      -> notify (kind "working")  optional, opt-in
//	-> idle         -> notify (kind "idle")     optional raw idle, opt-in
package decide

import "github.com/cobanov/herdr-ntfysh/internal/config"

// Decision is the outcome of evaluating a transition.
type Decision struct {
	Notify bool
	// Kind is the notification category used for wording, tags and priority:
	// "done", "blocked", "working" or "idle".
	Kind string
}

// Decide evaluates a transition from prev to cur against the configured
// notify set. prev is the last status seen for the pane ("" if unknown).
func Decide(cfg *config.Config, prev, cur string) Decision {
	switch cur {
	case "done":
		// Explicit completion rollup from herdr. Repeated "done" emissions
		// are held back by the caller's debounce window, not here, so that
		// two genuinely separate completions both notify.
		if cfg.NotifyOn["done"] {
			return Decision{Notify: true, Kind: "done"}
		}
	case "blocked":
		// Entering blocked (avoid re-notifying on a repeated blocked event).
		if cfg.NotifyOn["blocked"] && prev != "blocked" {
			return Decision{Notify: true, Kind: "blocked"}
		}
	case "idle":
		// A turn just finished: was working, now idle.
		if cfg.NotifyOn["done"] && prev == "working" {
			return Decision{Notify: true, Kind: "done"}
		}
		// Opt-in raw idle for any entry into idle.
		if cfg.NotifyOn["idle"] && prev != "idle" {
			return Decision{Notify: true, Kind: "idle"}
		}
	case "working":
		if cfg.NotifyOn["working"] && prev != "working" {
			return Decision{Notify: true, Kind: "working"}
		}
	}
	return Decision{}
}
