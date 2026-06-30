---
name: event-schedule-verification
description: Verify event/conference schedule details from official dynamic schedule pages before acting on signals, calendar suggestions, or user-facing summaries.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [events, calendar, schedules, verification, browser]
---

# Event Schedule Verification

Use this when a task involves confirming public event / conference schedule details, especially when a signal, email, or note contains dates/times that may be wrong.

## When to Use

- A user asks to verify talks, panels, conference sessions, meetups, or event dates.
- A signal or note says "attend/register/coordinate" for a public event.
- Dates and weekdays do not line up, or the user flags a likely date error.
- Search results are blocked, stale, or inconsistent with an official event site.

## Workflow

1. **Check the calendar math first**
   - Use a tool, not mental math, to verify weekday/date alignment:
     ```bash
     python3 - <<'PY'
     import datetime
     for d in ['2026-05-05','2026-05-06','2026-05-07','2026-05-08']:
         dt = datetime.date.fromisoformat(d)
         print(d, dt.strftime('%A'))
     PY
     ```

2. **Prefer the official event schedule over search snippets**
   - Go directly to the event's official site when known.
   - For Boulder Startup Week, the official schedule is reachable from:
     - `https://boulderstartupweek.com/` → `VIEW SCHEDULE`
   - Search engines may be blocked by bot checks or return poor results; do not stop there.

3. **Handle dynamic schedule pages with browser DOM inspection**
   - If the page is a JavaScript app, use browser tools and `browser_console` to search `document.body.innerText` for exact session titles, speaker names, or companies.
   - Find the surrounding day section by walking up the DOM from the matching title. Example pattern:
     ```js
     const title = 'Session title here';
     const h = [...document.querySelectorAll('h3')].find(el => el.innerText.includes(title));
     const day = h.closest('.day-section');
     const card = h.closest('.session-card');
     ({ date: day?.dataset.date, dayTitle: day?.querySelector('h2')?.innerText, cardText: card?.innerText });
     ```
   - Click the session card and inspect the modal for full details: time, venue, description, facilitator/speaker, registration count, and topics.

4. **Report corrected details clearly**
   - State the official source used.
   - Present the corrected date, weekday, time, venue, title, and speaker/facilitator.
   - Explicitly name any correction from the original source, e.g.:
     - `Tuesday, May 6` → `Tuesday, May 5`
     - `Thursday, May 8` → `Thursday, May 7`

5. **Do not mutate signals/calendar entries unless asked**
   - If you discovered a C-Core or vault signal has wrong event details, report the correction first.
   - Only update the signal, register, or add calendar holds with explicit user approval.

## Verification Checklist

Before finalizing:
- Weekdays/dates were verified by a tool.
- Details came from the official event schedule when available.
- Dynamic-page content was inspected beyond snippets when needed.
- Any original-source errors are called out directly.
- No outbound communication, registration, signal edit, or calendar mutation was made without approval.
