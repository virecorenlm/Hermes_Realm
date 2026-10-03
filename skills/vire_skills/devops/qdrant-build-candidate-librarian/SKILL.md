---
name: qdrant-build-candidate-librarian
description: "Use when converting retrieved project notes into a deduplicated, report-only build queue."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Build candidate librarian

This is a companion-project pattern; the implementation is not included here. Gather source documents from a configured Qdrant collection, group related proposals, and classify each as new, partial, already built, merge only, or archive reference. Check the current filesystem and task history before creating work. Write a review report first; never create or execute projects merely because a retrieved note proposes one.
