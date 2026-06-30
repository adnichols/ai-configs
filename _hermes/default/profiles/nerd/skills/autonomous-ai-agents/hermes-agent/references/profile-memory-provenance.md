# Profile memory provenance checks

Use when a user asks whether a Hermes profile imported/copied memories at creation or what the agent already knows from memory.

## Fast evidence-gathering pattern

1. Confirm active profile and path:
   ```bash
   hermes profile show <profile>
   ```
2. Inspect durable memory/user-profile files under the profile, without exposing secrets:
   ```bash
   find ~/.hermes/profiles/<profile> -maxdepth 3 -type f | grep -Ei 'memories|memory|profile|SOUL.md'
   sed -n '1,200p' ~/.hermes/profiles/<profile>/memories/MEMORY.md
   ```
3. Compare file birth/modify time to profile directory birth time on macOS:
   ```bash
   stat -f 'birth=%SB modify=%Sm change=%Sc path=%N' -t '%Y-%m-%d %H:%M:%S %Z' \
     ~/.hermes/profiles/<profile>/memories/MEMORY.md \
     ~/.hermes/profiles/<profile>
   ```
   If the memory file birth/modify time predates the profile directory birth time, say it appears imported/copied into the profile. Avoid claiming the exact source unless logs/transcripts prove it.
4. Search sessions/logs for stronger provenance if needed:
   ```bash
   grep -RniE 'profile|clone|import|memory|memories' ~/.hermes/profiles/<profile>/logs ~/.hermes/profiles/<profile>/sessions 2>/dev/null | head -100
   ```
5. Summarize what the current injected memory says, distinguishing:
   - live injected memory/user profile facts;
   - evidence from files/logs;
   - inference about import/copy provenance;
   - unknowns.

## Pitfalls

- Do not treat injected memory as evidence of the current machine state; use live file/CLI checks for system/profile state.
- Do not overclaim provenance. File timestamps can show likely copied/imported memories, but not whether the source was clone, export/import, or manual copy unless corroborated.
- Redact tokens, bot IDs, and secrets when reading profile config/logs; prefer focused files over dumping `.env` or full config.
