# Development status — 0.2.4

Roadmap stage: Activity System. Explainable participation ideas added in Community → Mitmachimpulse, with a shortcut from Activity. Suggestions cover conversation starts, Lobby Night proposals and Creator introductions. Text can be edited and copied; no outgoing Discord messages or API requests occur.

Only confirmed 24h captures no older than six hours drive activity-specific suggestions. Empty/unconfirmed, capped, old, invalid or legacy records use general suggestions and explain the data gap. Thresholds (zero messages; up to three participants; more participants) are explicit simple heuristics, not a server-wide diagnosis. No author IDs or tokens are included. Edited drafts survive same-channel refreshes, including recommendation changes.

Validation: 18 unit tests including recommendation branches, data-gap handling and no private fields in drafts; existing updater/credential/activity tests passed. UI checks verify tab navigation, clipboard, unsent status and edited draft retention. No real Discord writes or paid AI calls.

Next roadmap stage: reviewed Lobby Night voting integration. Dependencies and launcher protocol unchanged.
