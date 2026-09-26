---
name: audit-adn
description: Audit the ADN install against the pinned manifest. Fail closed on missing files, checksums, roles, or markers.
---

ADN_RUNTIME_MARKER:audit-adn:ecc249f1e306fc64ddf83c7bed16cacf7c2239db

Run `bun ~/.agents/adn/scripts/audit-adn.ts`. Compare live files to manifest checksums and markers. Fail closed on missing required sources or roles. Do not silently refresh the pin.
