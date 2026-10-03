---
name: vire-local-mcp-services
description: "Use when inspecting or configuring optional local MCP servers for Hermes Realm."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Local MCP services

MCP servers are optional companion programs. Inspect the server's process, bind address, transport, and declared tools before adding it to Hermes. Register compatible servers in the upstream Hermes MCP configuration. Keep local-only servers on loopback; require authentication and network controls for remote access.

For a Qdrant-backed tool, read `QDRANT_URL` from configuration and verify the target collection and embedding dimensions before changing a route. Test the actual MCP transport rather than assuming `/health` exists. This repository does not ship a preconfigured MCP server or a private node map.
