# Public sanitization report

## Scope

This history-free working tree was prepared for a first public commit. No commit, push, remote, or public repository was created.

## Changes

- Removed one private operational summary, one private baseline audit, and 17 obsolete archived skill snapshots. Active skills and reusable concepts remain.
- Replaced fixed LAN service maps with loopback defaults and configurable service URLs. Realm paths now use `HERMES_REALM_HOME` or the XDG configuration directory by default.
- Generalized voice model, Gmail, business integration, systemd, cron, identity, and operator-permission examples.
- Added a tracked placeholder-only `.env.example`; filled environment files and local secrets remain ignored.
- Replaced private autonomy language with operator-controlled boundaries. Generated queue plans now await review; shell and HTTP tasks require explicit opt-in.
- Aligned active skill `license` metadata with the repository's existing MIT license. Existing author attribution was retained.
- Kept the generic `origin/` explanation and upstream Hermes-owned paths.

## Verification

- Final working-tree Gitleaks `--no-git` scan: 0 findings, exit code 0.
- Private-address, private-path, account, machine-name, and personal-context searches: 0 operational matches.
- Private-key signature, recognized token-shape, and conflict-marker searches: 0 matches.
- Python `compileall` for scripts, cron pulses, and workforce: passed.
- Offline workforce smoke test: 9/9 checks passed.
- Offline service URL, application path, and task-gate checks: passed.
- Git staging and remote checks: no staged files and no remote.

## Residual matches

- 32 skill `author` metadata lines retain legitimate attribution (safe public attribution).
- Loopback URLs, placeholder account names, credential variable names, and upstream Hermes/OpenClaw paths are generic examples, not private operational configuration.
- No findings were classified as requiring further privacy cleanup.

## Human review

- Review optional companion skill procedures before use; some referenced programs and workflows are not shipped in this repository.
- Test voice hardware, upstream Hermes CLI compatibility, live external integrations, and the optional hardware-specific Redis override on the intended deployment. These require local services or accounts and were not part of offline validation.
