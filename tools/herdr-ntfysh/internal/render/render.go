// Package render turns a herdr event and the resolved config into an ntfy
// Message: title, body, tags and priority.
//
// Emoji are expressed as ntfy tag shortcodes (e.g. "white_check_mark")
// rather than raw Unicode in headers. ntfy renders matching shortcodes as
// emoji in front of the title, and this keeps HTTP headers ASCII-clean so no
// proxy mangles them. Free-form Unicode is only ever placed in the request
// body, where it is safe.
package render

import (
	"fmt"
	"strings"

	"github.com/cobanov/herdr-ntfysh/internal/config"
	"github.com/cobanov/herdr-ntfysh/internal/event"
	"github.com/cobanov/herdr-ntfysh/internal/ntfy"
)

// statusTag maps an agent status to its ntfy emoji shortcode.
var statusTag = map[string]string{
	"done":    "white_check_mark",
	"blocked": "rotating_light",
	"working": "hourglass_flowing_sand",
	"idle":    "zzz",
}

// statusWord is the human phrasing used in the notification title.
var statusWord = map[string]string{
	"done":    "done",
	"blocked": "needs input",
	"working": "working",
	"idle":    "idle",
}

// EventMessage builds the notification for a triggering event. kind is the
// decided notification category ("done", "blocked", "working", "idle"), which
// may differ from the raw agent status — e.g. a working->idle transition is
// surfaced as "done".
func EventMessage(cfg *config.Config, ev *event.Event, kind string) ntfy.Message {
	agent := ev.Agent()
	if cfg.SessionTitle {
		if s := ev.SessionTitle(); s != "" {
			agent = s
		}
	}

	// ASCII separator on purpose: X-Title is an HTTP header and must stay
	// ISO-8859-1/ASCII clean, or non-ASCII bytes get mojibaked by proxies.
	title := fmt.Sprintf("%s - %s", agent, wordFor(kind))
	if cfg.TitlePrefix != "" {
		title = cfg.TitlePrefix + " " + title
	}

	return ntfy.Message{
		Title:    title,
		Body:     buildBody(cfg, ev, kind),
		Tags:     buildTags(cfg, kind),
		Priority: cfg.PriorityFor(kind),
		Click:    cfg.Click,
		Icon:     cfg.Icon,
		Markdown: cfg.Markdown,
	}
}

// TestMessage builds the notification sent by the `--test` action.
func TestMessage(cfg *config.Config) ntfy.Message {
	body := fmt.Sprintf("If you can read this, herdr-ntfysh can reach your ntfy server.\n\n📍 %s/%s", cfg.Server, cfg.Topic)
	return ntfy.Message{
		Title:    joinPrefix(cfg.TitlePrefix, "herdr-ntfysh - test"),
		Body:     body,
		Tags:     append([]string{"test_tube", "white_check_mark"}, cfg.TagsExtra...),
		Priority: 3,
		Click:    cfg.Click,
		Icon:     cfg.Icon,
		Markdown: cfg.Markdown,
	}
}

// buildBody assembles the message body: a one-line detail followed by the
// pane location breadcrumb.
func buildBody(cfg *config.Config, ev *event.Event, status string) string {
	var b strings.Builder
	b.WriteString(detailFor(ev, status))
	if loc := ev.Location(); loc != "" {
		b.WriteString("\n\n📍 ")
		b.WriteString(loc)
	}
	if n := cfg.BodyLines; n > 0 {
		if out := ev.RecentOutput(n); out != "" {
			b.WriteString("\n\n")
			b.WriteString(out)
		}
	}
	return b.String()
}

// detailFor chooses the most specific description available for a status,
// preferring explicit labels/custom status over a generic sentence.
func detailFor(ev *event.Event, status string) string {
	switch status {
	case "blocked":
		return firstNonEmpty(ev.ErrorLabel(), ev.CustomStatus(), "Agent is blocked and waiting for your input.")
	case "done":
		return firstNonEmpty(ev.TaskLabel(), ev.CustomStatus(), "Agent finished its task.")
	case "working":
		return firstNonEmpty(ev.CustomStatus(), ev.TaskLabel(), "Agent started working.")
	case "idle":
		return firstNonEmpty(ev.CustomStatus(), "Agent is idle.")
	default:
		return firstNonEmpty(ev.CustomStatus(), fmt.Sprintf("Agent status: %s", status))
	}
}

// buildTags combines the status emoji shortcode with any user-supplied extras.
func buildTags(cfg *config.Config, status string) []string {
	tags := make([]string, 0, 1+len(cfg.TagsExtra))
	if tag, ok := statusTag[status]; ok {
		tags = append(tags, tag)
	}
	tags = append(tags, cfg.TagsExtra...)
	return tags
}

func wordFor(status string) string {
	if w, ok := statusWord[status]; ok {
		return w
	}
	return status
}

func joinPrefix(prefix, s string) string {
	if prefix == "" {
		return s
	}
	return prefix + " " + s
}

func firstNonEmpty(vals ...string) string {
	for _, v := range vals {
		if s := strings.TrimSpace(v); s != "" {
			return s
		}
	}
	return ""
}
