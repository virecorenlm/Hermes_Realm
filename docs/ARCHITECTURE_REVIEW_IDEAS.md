# Architecture ideas

The file-backed workforce has an offline smoke test and a shared agent helper. Potential future work:

- Add CI for Python syntax and the workforce smoke test.
- Route model-generated task plans into a separate operator review queue before promotion.
- Extract shared Qdrant embedding and retry behavior from the scripts.
- Document optional voice and vision dependency versions on tested platforms.

The trusted queue runner gates shell and HTTP tasks with explicit environment switches. Its queue must still be writable only by trusted local processes.
