---
name: audit-adn
description: Audit the ADN install against the pinned manifest. Fail closed on missing files, checksums, roles, or markers.
---

ADN_RUNTIME_MARKER:audit-adn:e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a

Run `bun ~/.agents/adn/scripts/audit-adn.ts`. Compare live files to manifest checksums and markers. Fail closed on missing required sources or roles. Do not silently refresh the pin.
