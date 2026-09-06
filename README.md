# Incident Lab for Hermes

Opt-in native Hermes plugin that observes exhausted API errors and failed tool results using trusted session IDs, stores only sanitized failure classes/counts/timestamps in profile-owned plugin state, and injects a bounded recovery/prevention reminder on the next turn.

## Install
```sh
hermes plugins install seojoonkim/hermes-plugin-incidentlab --ref RELEASE_COMMIT_SHA --enable
hermes plugins doctor incidentlab --ci
```
Use the immutable commit SHA from the latest release. Start a fresh session; restart a gateway only when no work will be interrupted. For each named profile, run the same command with `hermes --profile NAME`.

## Boundaries
This plugin does not store prompts, tool arguments/results, provider messages, URLs, or credentials. It ignores intermediate retries and events without session identity. It does not verify root cause, run tests, modify code, complete tasks, change approvals, replay messages, or restart services. It is a reminder/incident observer, not autonomous remediation. Plugin state is local and not tamper-proof.

The manual incident ledger and OpenClaw-compatible skill are in [agent-incident-lab](https://github.com/seojoonkim/agent-incident-lab).

## Verify from source
```sh
hermes plugins doctor . --ci
```

MIT licensed.
