---
name: mcp-client-tools
description: "Connect to and use MCP (Model Context Protocol) servers: native built-in client, mcporter CLI bridge, and TouchDesigner MCP."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, model-context-protocol, mcporter, touchdesigner]
    related_skills: []
---

# MCP Client Tools

Model Context Protocol (MCP) servers expose tools and resources that Hermes can discover and call. There are two ways to use them: the **native built-in client** (automatic tool discovery) and the **mcporter CLI bridge** (ad-hoc server interaction).

## Native MCP Client

Servers configured in `config.yaml` are automatically discovered and registered as Hermes tools.

### config.yaml
```yaml
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    transport: stdio        # or http for remote servers
```

### Discovery
Restart Hermes (or `/reset`) after adding a server. Tools appear in the toolset.

### stdio vs HTTP
- **stdio:** local subprocess; tools auto-registered; works offline
- **HTTP:** remote endpoint; useful for shared infrastructure; requires network

## mcporter CLI Bridge

Ad-hoc interaction with any MCP server without editing `config.yaml`.

### Install
```bash
pip install mcporter
```

### List Servers
```bash
mcporter list
```

### Call a Tool
```bash
mcporter call <server-name> <tool-name> '{"arg": "value"}'
```

### Configure a New Server
```bash
mcporter add <name> --command "npx -y @modelcontextprotocol/server-filesystem /tmp"
mcporter add <name> --url "http://localhost:3000/sse" --transport http
```

### Auth
For servers requiring authentication:
```bash
mcporter auth <name> --token "<api-key>"
mcporter auth <name> --header "Authorization: Bearer <token>"
```

### Pitfalls
- `mcporter` only supports stdio and HTTP transports; SSE is HTTP under the hood
- Server process must stay alive for the duration of the session
- JSON args must be single-quoted on shell to prevent interpolation

## TouchDesigner MCP

Control a running TouchDesigner instance via the TwoZero MCP server.

### Prerequisites
- TouchDesigner running with TwoZero extension loaded
- MCP server configured (native or mcporter)

### Common Operations
- Query network structure (`/project`, `/project/geo1`)
- Set parameter values
- Trigger cook/render
- Read texture data

### Example
```python
# Via native MCP tool (if configured)
touchdesigner_mcp(query="/project/geo1")  # Returns node tree
touchdesigner_mcp(set_param={"path": "/project/geo1/tx", "value": 5.0})
```

### Pitfalls
- TouchDesigner must be running before the MCP server starts
- Network paths are case-sensitive
- Cook operations are blocking — large networks may timeout
