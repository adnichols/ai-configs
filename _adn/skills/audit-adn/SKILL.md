---
name: audit-adn
description: Audit the ADN install against the pinned manifest. Fail closed on missing files, checksums, roles, or markers.
---

ADN_RUNTIME_MARKER:audit-adn:46756f89270d7e7dcb8c28c90fd0f957ade4ce2c

Run `bun ~/.agents/adn/scripts/audit-adn.ts`. Compare live files to manifest checksums and markers. Fail closed on missing required sources or roles. Do not silently refresh the pin.
