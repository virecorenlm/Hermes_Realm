---
name: qdrant-source-reassembler
description: "Use when reassembling a complete source document from chunked Qdrant payloads."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Source reassembly pattern

Match points by exact source identifier, order chunks using explicit sequence metadata, and verify coverage before calling a document complete. Preserve raw output locally and inspect it before building from the notes. Treat uncertain chunk order or missing sections as incomplete. A companion implementation may be written against the configured `QDRANT_URL`; none is included here.
