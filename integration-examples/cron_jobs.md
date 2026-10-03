# Optional cron examples

Set the checkout path in your user crontab and run only jobs whose dependencies you configured. Cron does not load your interactive shell environment; source a private environment file when needed. Review output destinations before scheduling.

```cron
HERMES_REALM_REPO=/path/to/Hermes_Realm
0 7 * * * cd "$HERMES_REALM_REPO" && python3 workforce/queen_orchestrator.py status
0 6 * * * cd "$HERMES_REALM_REPO" && python3 scripts/memory_sync_qwen3.py
```

The memory job requires configured Ollama and Qdrant services. No scheduled external posting or purchases are included.
