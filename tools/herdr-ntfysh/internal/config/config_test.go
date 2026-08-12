package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParsePriority(t *testing.T) {
	cases := map[string]int{
		"":         3,
		"min":      1,
		"low":      2,
		"default":  3,
		"high":     4,
		"max":      5,
		"urgent":   5,
		"4":        4,
		"nonsense": 3, // falls back to def
	}
	for in, want := range cases {
		if got := parsePriority(in, 3); got != want {
			t.Errorf("parsePriority(%q) = %d, want %d", in, got, want)
		}
	}
}

func TestParseStatuses(t *testing.T) {
	got := parseStatuses("done, BLOCKED, bogus", []string{"done"})
	if !got["done"] || !got["blocked"] {
		t.Errorf("expected done+blocked, got %v", got)
	}
	if got["bogus"] {
		t.Errorf("unknown status should be dropped, got %v", got)
	}
	// Empty input falls back to defaults.
	if def := parseStatuses("", []string{"working"}); !def["working"] || len(def) != 1 {
		t.Errorf("expected default working set, got %v", def)
	}
}

func TestParseBool(t *testing.T) {
	for _, v := range []string{"1", "true", "yes", "on"} {
		if !parseBool(v, false) {
			t.Errorf("parseBool(%q) should be true", v)
		}
	}
	for _, v := range []string{"0", "false", "no", "off"} {
		if parseBool(v, true) {
			t.Errorf("parseBool(%q) should be false", v)
		}
	}
	if !parseBool("garbage", true) {
		t.Error("parseBool should return default on garbage")
	}
}

func TestParseEnvFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, ".env")
	content := "# comment\n\nexport HERDR_NTFY_TOPIC=herd\nHERDR_NTFY_TOKEN=\"tk_secret\"\nBAD LINE\n"
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	vals, err := parseEnvFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if vals["HERDR_NTFY_TOPIC"] != "herd" {
		t.Errorf("topic = %q", vals["HERDR_NTFY_TOPIC"])
	}
	if vals["HERDR_NTFY_TOKEN"] != "tk_secret" {
		t.Errorf("token quotes not stripped: %q", vals["HERDR_NTFY_TOKEN"])
	}
}

func TestLoadValidation(t *testing.T) {
	clearEnv(t)
	// Enabled but no server/topic -> error.
	t.Setenv("HERDR_NTFY_ENABLED", "true")
	if _, err := Load(); err == nil {
		t.Error("expected error for missing server/topic")
	}

	// Server without scheme -> error.
	t.Setenv("HERDR_NTFY_SERVER", "ntfy.example.com")
	t.Setenv("HERDR_NTFY_TOPIC", "herd")
	if _, err := Load(); err == nil {
		t.Error("expected error for scheme-less server")
	}

	// Valid config.
	t.Setenv("HERDR_NTFY_SERVER", "https://ntfy.example.com/")
	cfg, err := Load()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.Server != "https://ntfy.example.com" {
		t.Errorf("trailing slash not trimmed: %q", cfg.Server)
	}
	if !cfg.NotifyOn["done"] || !cfg.NotifyOn["blocked"] {
		t.Errorf("default notify set wrong: %v", cfg.NotifyOn)
	}
	if cfg.PriorityFor("blocked") != 4 {
		t.Errorf("default blocked priority = %d, want 4", cfg.PriorityFor("blocked"))
	}
}

func TestDisabledSkipsValidation(t *testing.T) {
	clearEnv(t)
	t.Setenv("HERDR_NTFY_ENABLED", "false")
	cfg, err := Load()
	if err != nil {
		t.Fatalf("disabled config should not error: %v", err)
	}
	if cfg.Enabled {
		t.Error("expected disabled")
	}
}

// clearEnv removes every HERDR_NTFY_* and the config-dir vars so a test starts
// from a known baseline. t.Setenv restores originals after the test.
func clearEnv(t *testing.T) {
	t.Helper()
	for _, k := range []string{
		"HERDR_NTFY_ENABLED", "HERDR_NTFY_SERVER", "HERDR_NTFY_TOPIC",
		"HERDR_NTFY_TOKEN", "HERDR_NTFY_USERNAME", "HERDR_NTFY_PASSWORD",
		"HERDR_NTFY_NOTIFY_ON", "HERDR_NTFY_ENV_FILE", "HERDR_PLUGIN_CONFIG_DIR",
	} {
		if _, ok := os.LookupEnv(k); ok {
			t.Setenv(k, "")
			os.Unsetenv(k)
		}
	}
	// Point env-file lookup at an empty dir so a stray ./.env can't leak in.
	t.Setenv("HERDR_NTFY_ENV_FILE", filepath.Join(t.TempDir(), "none"))
}
