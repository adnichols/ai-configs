// Package ntfy is a tiny, dependency-free client for publishing to an ntfy
// server. It speaks ntfy's HTTP header protocol directly over the standard
// library, and supports Bearer/Basic auth plus custom-CA and insecure TLS so
// it works against self-hosted instances.
package ntfy

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/cobanov/herdr-ntfysh/internal/config"
)

// Message is a single ntfy publication.
type Message struct {
	Title    string
	Body     string
	Tags     []string
	Priority int
	Click    string
	Icon     string
	Markdown bool
}

// Client publishes messages to a configured ntfy server.
type Client struct {
	cfg  *config.Config
	http *http.Client
}

// New builds a Client with a TLS configuration derived from cfg.
func New(cfg *config.Config) *Client {
	transport := http.DefaultTransport.(*http.Transport).Clone()

	tlsCfg := &tls.Config{MinVersion: tls.VersionTLS12}
	custom := false
	if cfg.TLSInsecure {
		tlsCfg.InsecureSkipVerify = true // opt-in, for self-signed certs
		custom = true
	}
	if cfg.CAFile != "" {
		if pem, err := os.ReadFile(cfg.CAFile); err == nil {
			pool := x509.NewCertPool()
			if pool.AppendCertsFromPEM(pem) {
				tlsCfg.RootCAs = pool
				custom = true
			}
		}
	}
	if custom {
		transport.TLSClientConfig = tlsCfg
	}

	return &Client{
		cfg: cfg,
		http: &http.Client{
			Timeout:   time.Duration(cfg.TimeoutSec) * time.Second,
			Transport: transport,
		},
	}
}

// Publish sends a single message, returning an error on transport failure or
// a non-2xx response.
func (c *Client) Publish(m Message) error {
	url := strings.TrimRight(c.cfg.Server, "/") + "/" + c.cfg.Topic

	req, err := http.NewRequest(http.MethodPost, url, strings.NewReader(m.Body))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}

	if m.Title != "" {
		req.Header.Set("X-Title", m.Title)
	}
	if m.Priority >= 1 && m.Priority <= 5 {
		req.Header.Set("X-Priority", strconv.Itoa(m.Priority))
	}
	if len(m.Tags) > 0 {
		req.Header.Set("X-Tags", strings.Join(m.Tags, ","))
	}
	if m.Click != "" {
		req.Header.Set("X-Click", m.Click)
	}
	if m.Icon != "" {
		req.Header.Set("X-Icon", m.Icon)
	}
	if m.Markdown {
		req.Header.Set("X-Markdown", "yes")
	}

	// Auth: an access token wins over basic credentials when both are set.
	switch {
	case c.cfg.Token != "":
		req.Header.Set("Authorization", "Bearer "+c.cfg.Token)
	case c.cfg.Username != "":
		req.SetBasicAuth(c.cfg.Username, c.cfg.Password)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("post to ntfy: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		snippet, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		return fmt.Errorf("ntfy returned %s: %s", resp.Status, strings.TrimSpace(string(snippet)))
	}
	_, _ = io.Copy(io.Discard, resp.Body)
	return nil
}
