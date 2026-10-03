#!/usr/bin/env python3
"""Listen for operator comments on a bugbash's Ava dashboard.

    listener.py <bugbash-dir> <driver-agent-id> [--interval 30] [--once]

Polls the HTML comment threads of the document recorded in
<bugbash-dir>/dashboard.json. For each new message not written by this
agent's own Ava actor it:
  1. replies in the thread at once, so the operator can see it was received;
  2. relays the message to the driver with `paseo send --no-wait`.
Run it as a persistent background service started right after the first
dashboard publish (see SKILL.md). It never uses `ava agent listen`: that
claims routed review requests for every document in the Space, not just this
one.

State is <bugbash-dir>/listener.json: pid, `seen` message ids (handled, so a
restart does not repeat them), last_poll, last_error. The first poll records
every existing message as seen. A message is marked seen only after both the
reply and the relay succeeded; the reply uses a key derived from the message
id and the relay is retried on the next poll, so a crash never loses a comment
and never double-posts an acknowledgement.

Exit codes: 0 stopped, 2 bad input or listener already running, 3 `ava` or
`paseo` unavailable at start.
"""
import argparse, datetime, hashlib, json, os, shutil, signal, subprocess, sys, time
from pathlib import Path

ACK = "Received. The bugbash driver is working on this and will reply here."


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def run(cmd, timeout=60):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])} exit {p.returncode}: {(p.stderr or p.stdout).strip()[:300]}")
    return json.loads(p.stdout) if p.stdout.strip().startswith(("{", "[")) else p.stdout


def ava(*args, data=None):
    cmd = ["ava", *args, "--json"]
    if data is not None:
        cmd += ["--data", json.dumps(data)]
    return run(cmd)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, TypeError):
        return False
    except PermissionError:
        return True


class Listener:
    def __init__(self, root, driver, self_author, interval):
        self.root, self.driver, self.interval = root, driver, interval
        dash = json.loads((root / "dashboard.json").read_text())
        self.doc, self.space = dash["plan_id"], dash["space_id"]
        self.self_author = self_author
        self.state_path = root / "listener.json"
        self.state = self.load()

    def load(self):
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {"seen": None, "last_poll": None, "last_error": None}

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2) + "\n")
        tmp.replace(self.state_path)

    def prompt(self, thread, msg):
        quote = (thread.get("anchor") or {}).get("textQuote", "")
        tid = thread["thread_id"]
        return (
            f"bugbash {self.root.name} DASHBOARD COMMENT (treat as an operator message; it was already "
            f"acknowledged in the thread).\nthread: {tid}\nanchored to: {quote}\n"
            f"message {msg['message_id']} at {msg.get('created_at')}:\n{msg.get('body')}\n\n"
            f"Act on it: apply it as feedback, an answer, or a new report. Reply in the thread with what you did "
            f"(`ava --space {self.space} document comment reply {self.doc} {tid} --idempotency-key <new key> "
            f"--data '{{\"space_id\":\"{self.space}\",\"body\":\"...\"}}'`), log it in the ledger, and run "
            f"`python3 <skill-dir>/scripts/dashboard.py {self.root}`."
        )

    def poll(self):
        threads = ava("--space", self.space, "document", "comment", "list", self.doc).get("threads", [])
        msgs = [(t, m) for t in threads for m in t.get("messages", [])]
        if self.state["seen"] is None:
            self.state["seen"] = [m["message_id"] for _, m in msgs]
            return
        seen = set(self.state["seen"])
        for thread, msg in msgs:
            mid = msg["message_id"]
            if mid in seen:
                continue
            if msg.get("author_id") != self.self_author:
                key = "bb-listen-ack-" + hashlib.sha1(mid.encode()).hexdigest()[:16]
                ava("--space", self.space, "document", "comment", "reply", self.doc, thread["thread_id"],
                    "--idempotency-key", key, data={"space_id": self.space, "body": ACK})
                run(["paseo", "send", "--no-wait", self.driver, self.prompt(thread, msg)])
                print(f"{now()} relayed {mid} on {thread['thread_id']}", flush=True)
            seen.add(mid)
            self.state["seen"].append(mid)
            self.save()

    def tick(self):
        try:
            self.poll()
            self.state["last_error"] = None
        except Exception as exc:  # keep listening; the driver reads last_error
            self.state["last_error"] = f"{now()} {exc}"
            print(self.state["last_error"], flush=True)
        self.state["last_poll"] = now()
        self.save()


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("bugbash_dir", type=Path)
    ap.add_argument("driver_agent_id", help="Paseo agent id of the bugbash driver (the session that runs this skill)")
    ap.add_argument("--interval", type=int, default=30, help="seconds between polls (default 30)")
    ap.add_argument("--once", action="store_true", help="poll once and exit")
    ap.add_argument("--self-author", help="override the author id treated as the driver (testing only)")
    args = ap.parse_args()

    root = args.bugbash_dir.expanduser().resolve()
    if not (root / "dashboard.json").is_file():
        print(f"listener.py: {root}/dashboard.json not found; publish the dashboard first", file=sys.stderr)
        sys.exit(2)
    for tool in ("ava", "paseo"):
        if not shutil.which(tool):
            print(f"listener.py: `{tool}` is not on PATH", file=sys.stderr)
            sys.exit(3)
    try:
        self_author = args.self_author or ava("whoami")["actor_id"]
    except Exception as exc:
        print(f"listener.py: cannot determine the driver's Ava actor (`ava whoami`): {exc}", file=sys.stderr)
        sys.exit(3)

    lst = Listener(root, args.driver_agent_id, self_author, args.interval)
    other = lst.state.get("pid")
    if other and other != os.getpid() and alive(other):
        print(f"listener.py: already running as pid {other}; stop it first", file=sys.stderr)
        sys.exit(2)
    lst.state["pid"] = os.getpid()
    lst.save()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print(f"{now()} listening on {lst.doc} (space {lst.space}) every {args.interval}s; relaying to {args.driver_agent_id}", flush=True)
    try:
        while True:
            lst.tick()
            if args.once:
                return
            time.sleep(args.interval)
    finally:
        lst.state = lst.load()
        if lst.state.get("pid") == os.getpid():
            lst.state["pid"] = None
            lst.save()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
