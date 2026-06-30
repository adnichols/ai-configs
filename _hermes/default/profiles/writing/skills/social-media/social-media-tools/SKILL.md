---
name: social-media-tools
description: "Interact with X/Twitter and Yuanbao: post, search, DM, manage media, query groups, and @mention users."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [twitter, x, yuanbao, social-media, post, search, dm]
    related_skills: []
---

# Social Media Tools

## X/Twitter (xurl CLI)

Post, search, send DMs, upload media, and use the v2 API via the `xurl` CLI.

### Setup
```bash
npm install -g xurl
xurl auth login          # OAuth 2.0 flow
xurl auth status
```

### Post
```bash
xurl post "Hello from Hermes!"
xurl post "Check this out" --media ./image.png
```

### Search
```bash
xurl search "machine learning" --limit 20
xurl search "from:elonmusk" --limit 10
```

### Direct Messages
```bash
xurl dm <user_id> "Hello!"
xurl dm list
```

### Media
```bash
xurl media upload ./video.mp4
xurl post "Video attached" --media <media_id>
```

### v2 API Raw
```bash
xurl api /2/tweets/search/recent --query '{"query":"AI","max_results":10}'
```

## X/Twitter (x-cli)

Alternative terminal client using official X API credentials.

### Setup
```bash
npm install -g x-cli
x-cli auth login
```

### Operations
```bash
x-cli timeline               # Home timeline
x-cli mentions               # Recent mentions
x-cli like <tweet_id>
x-cli retweet <tweet_id>
x-cli bookmarks
x-cli user <username>
```

### Choosing Between xurl and x-cli
- **xurl:** More features (DM, media upload, search), v2 API support
- **x-cli:** Simpler, official API, good for basic interactions

## Yuanbao (元宝)

Interact with Yuanbao groups: @mention users, query group info and members.

### Setup
Requires Yuanbao account credentials configured in Hermes.

### Common Operations
- Query group member list
- @mention specific users in group chats
- Retrieve group information and metadata

### Use Cases
- Cross-platform community management
- Automated group announcements
- Member lookup and verification

## Cross-Platform Workflow

1. **Monitor:** `xurl search` for brand mentions or trends
2. **Curate:** Save relevant tweets for later
3. **Engage:** Reply or DM via `xurl`
4. **Archive:** Save thread content to `llm-wiki` or `note-taking-tools`
5. **Cross-post:** Share to Yuanbao groups when relevant

### Pitfalls
- Rate limits are strict on X v2 API; always check response headers
- Media uploads have size limits (5MB images, 512MB videos for some tiers)
- DM permissions require mutual follow for some account types
- Yuanbao group queries may require admin privileges
