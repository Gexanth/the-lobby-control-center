# Development status — 0.2.5

User-reported access issue fixed: the entire Community tab widget was disabled until a successful Discord overview load. Tabs now remain navigable offline. A direct connection button opens Discord settings. Local server ID selection permits offline planning, Creator management and stored activity review without reading or exposing the bot token. Same-server disconnect retains local context and data. Only live captures and current-server analysis require a matching connection.

Validation: 20 tests including new offscreen UI regressions for offline tab access, offline planning, direct connection shortcut, disconnect retention and wrong-server capture blocking. UI regressions now run in GitHub Actions with application dependencies installed. Existing source-update protocol unchanged.

Next: reviewed native Discord poll publishing for Lobby Night; no scheduled Discord event creation.
