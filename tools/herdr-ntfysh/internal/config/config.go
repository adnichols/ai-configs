// Package config resolves the plugin's runtime settings.
//
// Settings come from two layers, highest priority first:
//
//  1. Process environment variables (HERDR_NTFY_*). herdr passes the
//     invoking environment through, so this is handy for one-off overrides.
//  2. A .env file, looked up in HERDR_PLUGIN_CONFIG_DIR (the durable,
//     user-editable location herdr assigns per plugin), then the current
//     working directory as a fallback for standalone `--test` runs.
//
// Secrets (token, password) are never printed except as redacted markers.
package config

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// knownStatuses are the agent states herdr can report and that this plugin
// understands. Anything outside this set in HERDR_NTFY_NOTIFY_ON is ignored.
var knownStatuses = map[string]bool{
	"done":    true,
	"blocked": true,
	"working": true,
	"idle":    true,
}

// Config is the fully resolved, validated configuration for a single run.
type Config struct {
	Enabled bool

	// Server is the ntfy base URL including scheme, e.g. https://ntfy.example.com.
	Server string
	// Topic is the ntfy topic to publish to.
	Topic string

	// Token is an ntfy access token (Bearer auth). Takes precedence over
	// Username/Password when set.
	Token string
	// Username and Password enable HTTP Basic auth.
	Username string
	Password string

	// NotifyOn is the set of agent statuses that trigger a push.
	NotifyOn map[string]bool
	// Priority maps an agent status to an ntfy priority (1..5).
	Priority map[string]int

	// TLSInsecure disables TLS certificate verification (self-signed certs).
	TLSInsecure bool
	// CAFile is a path to a PEM bundle used to verify the server certificate.
	CAFile string

	// DedupWindow is the number of seconds during which an identical
	// status for the same pane is suppressed. 0 disables debouncing.
	DedupWindow int
	// TimeoutSec bounds the HTTP request to the ntfy server.
	TimeoutSec int

	// Presentation extras.
	Click        string
	Icon         string
	TagsExtra    []string
	TitlePrefix  string
	Markdown     bool
	SessionTitle bool
	BodyLines    int

	// StateDir is where debounce state is persisted (HERDR_PLUGIN_STATE_DIR).
	StateDir string

	// Debug logs the raw event payload and decision to stderr.
	Debug bool
}

// Load resolves configuration from the environment and .env file.
func Load() (*Config, error) {
	fileVals := loadEnvFile()

	get := func(key string) string {
		if v, ok := os.LookupEnv(key); ok && strings.TrimSpace(v) != "" {
			return strings.TrimSpace(v)
		}
		return fileVals[key]
	}

	cfg := &Config{
		Enabled:      parseBool(get("HERDR_NTFY_ENABLED"), true),
		Server:       strings.TrimRight(get("HERDR_NTFY_SERVER"), "/"),
		Topic:        strings.Trim(get("HERDR_NTFY_TOPIC"), "/"),
		Token:        get("HERDR_NTFY_TOKEN"),
		Username:     get("HERDR_NTFY_USERNAME"),
		Password:     get("HERDR_NTFY_PASSWORD"),
		TLSInsecure:  parseBool(get("HERDR_NTFY_TLS_INSECURE"), false),
		CAFile:       get("HERDR_NTFY_CA_FILE"),
		DedupWindow:  parseInt(get("HERDR_NTFY_DEDUP_WINDOW"), 10),
		TimeoutSec:   parseInt(get("HERDR_NTFY_TIMEOUT"), 10),
		Click:        get("HERDR_NTFY_CLICK"),
		Icon:         get("HERDR_NTFY_ICON"),
		TagsExtra:    parseList(get("HERDR_NTFY_TAGS_EXTRA")),
		TitlePrefix:  get("HERDR_NTFY_TITLE_PREFIX"),
		Markdown:     parseBool(get("HERDR_NTFY_MARKDOWN"), false),
		SessionTitle: parseBool(get("HERDR_NTFY_SESSION_TITLE"), true),
		BodyLines:    parseInt(get("HERDR_NTFY_BODY_LINES"), 0),
		StateDir:     os.Getenv("HERDR_PLUGIN_STATE_DIR"),
		Debug:        parseBool(get("HERDR_NTFY_DEBUG"), false),
	}

	cfg.NotifyOn = parseStatuses(get("HERDR_NTFY_NOTIFY_ON"), []string{"done", "blocked"})
	cfg.Priority = map[string]int{
		"done":    parsePriority(get("HERDR_NTFY_PRIORITY_DONE"), 3),
		"blocked": parsePriority(get("HERDR_NTFY_PRIORITY_BLOCKED"), 4),
		"working": parsePriority(get("HERDR_NTFY_PRIORITY_WORKING"), 2),
		"idle":    parsePriority(get("HERDR_NTFY_PRIORITY_IDLE"), 2),
	}

	if cfg.TimeoutSec <= 0 {
		cfg.TimeoutSec = 10
	}

	if cfg.BodyLines < 0 {
		cfg.BodyLines = 0
	}

	if err := cfg.validate(); err != nil {
		return nil, err
	}
	return cfg, nil
}

// validate enforces the invariants an enabled plugin needs to publish.
func (c *Config) validate() error {
	if !c.Enabled {
		return nil
	}
	if c.Server == "" {
		return fmt.Errorf("HERDR_NTFY_SERVER is required (e.g. https://ntfy.example.com)")
	}
	if !strings.Contains(c.Server, "://") {
		return fmt.Errorf("HERDR_NTFY_SERVER must include a scheme, got %q (e.g. https://%s)", c.Server, c.Server)
	}
	if c.Topic == "" {
		return fmt.Errorf("HERDR_NTFY_TOPIC is required")
	}
	if len(c.NotifyOn) == 0 {
		return fmt.Errorf("HERDR_NTFY_NOTIFY_ON resolved to no valid statuses")
	}
	return nil
}

// PriorityFor returns the configured ntfy priority for a status, defaulting
// to 3 (ntfy's "default") for unknown statuses.
func (c *Config) PriorityFor(status string) int {
	if p, ok := c.Priority[status]; ok && p > 0 {
		return p
	}
	return 3
}

// PrintRedacted writes the resolved configuration to w with secrets masked.
func (c *Config) PrintRedacted(w interface{ Write([]byte) (int, error) }) {
	redact := func(s string) string {
		if s == "" {
			return "(unset)"
		}
		return "***set***"
	}
	fmt.Fprintf(w, "herdr-ntfysh configuration\n")
	fmt.Fprintf(w, "  enabled:       %t\n", c.Enabled)
	fmt.Fprintf(w, "  server:        %s\n", orUnset(c.Server))
	fmt.Fprintf(w, "  topic:         %s\n", orUnset(c.Topic))
	fmt.Fprintf(w, "  token:         %s\n", redact(c.Token))
	fmt.Fprintf(w, "  username:      %s\n", orUnset(c.Username))
	fmt.Fprintf(w, "  password:      %s\n", redact(c.Password))
	fmt.Fprintf(w, "  notify on:     %s\n", strings.Join(sortedKeys(c.NotifyOn), ", "))
	fmt.Fprintf(w, "  priority:      done=%d blocked=%d working=%d idle=%d\n",
		c.Priority["done"], c.Priority["blocked"], c.Priority["working"], c.Priority["idle"])
	fmt.Fprintf(w, "  tls insecure:  %t\n", c.TLSInsecure)
	fmt.Fprintf(w, "  ca file:       %s\n", orUnset(c.CAFile))
	fmt.Fprintf(w, "  dedup window:  %ds\n", c.DedupWindow)
	fmt.Fprintf(w, "  timeout:       %ds\n", c.TimeoutSec)
	fmt.Fprintf(w, "  markdown:      %t\n", c.Markdown)
	fmt.Fprintf(w, "  title prefix:  %s\n", orUnset(c.TitlePrefix))
	fmt.Fprintf(w, "  extra tags:    %s\n", orUnset(strings.Join(c.TagsExtra, ",")))
	fmt.Fprintf(w, "  session title: %t\n", c.SessionTitle)
	fmt.Fprintf(w, "  body lines:    %d\n", c.BodyLines)
	fmt.Fprintf(w, "  state dir:     %s\n", orUnset(c.StateDir))
}

// loadEnvFile finds and parses the .env file, returning an empty map if none
// exists. Lookup order: an explicit HERDR_NTFY_ENV_FILE, then the herdr
// plugin config dir, then ./.env.
func loadEnvFile() map[string]string {
	var candidates []string
	if p := os.Getenv("HERDR_NTFY_ENV_FILE"); p != "" {
		candidates = append(candidates, p)
	}
	if dir := os.Getenv("HERDR_PLUGIN_CONFIG_DIR"); dir != "" {
		candidates = append(candidates, filepath.Join(dir, ".env"))
	}
	candidates = append(candidates, ".env")

	for _, path := range candidates {
		if vals, err := parseEnvFile(path); err == nil {
			return vals
		}
	}
	return map[string]string{}
}

// parseEnvFile reads a dotenv-style file: KEY=VALUE lines, optional leading
// "export", # comments, blank lines, and single/double quoted values.
func parseEnvFile(path string) (map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	vals := map[string]string{}
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimPrefix(line, "export ")
		eq := strings.IndexByte(line, '=')
		if eq < 0 {
			continue
		}
		key := strings.TrimSpace(line[:eq])
		val := strings.TrimSpace(line[eq+1:])
		val = unquote(val)
		if key != "" {
			vals[key] = val
		}
	}
	return vals, sc.Err()
}

func unquote(s string) string {
	if len(s) >= 2 {
		if (s[0] == '"' && s[len(s)-1] == '"') || (s[0] == '\'' && s[len(s)-1] == '\'') {
			return s[1 : len(s)-1]
		}
	}
	return s
}

func parseBool(s string, def bool) bool {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "1", "true", "yes", "on", "y":
		return true
	case "0", "false", "no", "off", "n":
		return false
	default:
		return def
	}
}

func parseInt(s string, def int) int {
	if n, err := strconv.Atoi(strings.TrimSpace(s)); err == nil {
		return n
	}
	return def
}

// parsePriority accepts an ntfy priority as a number (1..5) or a name.
func parsePriority(s string, def int) int {
	s = strings.ToLower(strings.TrimSpace(s))
	switch s {
	case "":
		return def
	case "min", "1":
		return 1
	case "low", "2":
		return 2
	case "default", "3":
		return 3
	case "high", "4":
		return 4
	case "max", "urgent", "5":
		return 5
	}
	if n, err := strconv.Atoi(s); err == nil && n >= 1 && n <= 5 {
		return n
	}
	return def
}

func parseList(s string) []string {
	var out []string
	for _, p := range strings.Split(s, ",") {
		if p = strings.TrimSpace(p); p != "" {
			out = append(out, p)
		}
	}
	return out
}

// parseStatuses resolves the notify-on set, keeping only known statuses and
// falling back to def when nothing valid is supplied.
func parseStatuses(s string, def []string) map[string]bool {
	set := map[string]bool{}
	for _, p := range parseList(strings.ToLower(s)) {
		if knownStatuses[p] {
			set[p] = true
		}
	}
	if len(set) == 0 {
		for _, d := range def {
			set[d] = true
		}
	}
	return set
}

func sortedKeys(m map[string]bool) []string {
	// Small, fixed key space; a stable manual order reads better than sort.
	order := []string{"done", "blocked", "working", "idle"}
	var out []string
	for _, k := range order {
		if m[k] {
			out = append(out, k)
		}
	}
	return out
}

func orUnset(s string) string {
	if s == "" {
		return "(unset)"
	}
	return s
}
