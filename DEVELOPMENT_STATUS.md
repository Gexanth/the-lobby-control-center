# Development status — 0.2.3

Roadmap stage: Activity System. Bounded 24h collection now paginates up to five pages (500 messages), stopping when an older message is reached or a nonempty short page reaches the accessible history end. The aggregate includes explicit coverage status and window boundaries; bots excluded, message content and member IDs not retained. A full scan at the cap is marked incomplete. Empty responses are marked unconfirmed because missing Read Message History may return no messages. Historic 0.2.2 samples remain readable and marked as old samples.

Permissions errors show targeted feedback for invalid credentials, denied channel access and missing/inaccessible resources. Request limits do not trigger automatic retries. Page errors invalidate the run rather than saving a misleading partial sample; repeated cursors are rejected.

Validated: 15 unit tests including two-page cutoff, early stop, five-page cap, empty response, page failure and repeated cursor; existing storage/credentials/update tests retained. UI coverage rendering inspected with synthetic data during publication. No live Discord modifications or paid AI calls performed.

Next: participation suggestions and reviewed Lobby Night voting integration. Dependencies and launcher protocol unchanged.
