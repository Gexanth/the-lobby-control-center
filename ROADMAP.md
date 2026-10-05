# Community roadmap

Order authorized by the owner: Activity System → Lobby Night automation → Creator Hub → Dashboard → AI server analysis.

## 0.2.0: first integrated foundation

- Activity System: aggregate the last 100 messages in one selected text/announcement channel, excluding bots. Optional polling every 15 minutes while connected. Store counts, unique participant count and time range; never persist message content or author IDs. Samples are bounded, not complete server activity or trends.
- Lobby Night: local server-scoped date, suggestions and cancellation; copyable voting text; one-time app reminder at due time or next connection. No live Discord poll, event or outgoing message yet.
- Creator Hub: local Twitch/YouTube application records, accepted/paused status, editing and removal. No live status lookup, automatic roles or stream announcements yet.
- Dashboard: community counts for the connected server. Full charts and history pending.
- AI analysis: explicit analysis action uses the existing configured OpenAI connection; sends whitelisted aggregate samples, local event planning and creator status counts. No message content, bot credentials, creator names or links sent through this context. API response quality has not been tested against a live paid service.

## Next priorities

1. Activity history and consistent time windows, permissions feedback and participation prompts.
2. Reviewed Discord voting-message integration, delivery records and reminders that avoid duplicates. Always clarify whether scheduling depends on the desktop app remaining connected. Actual Discord event creation was previously withdrawn.
3. Creator workflows integrated with Discord roles and verified live-stream sources.
4. Dashboard trends based on real history, no invented metrics.
5. Expanded AI recommendations with evidence and sample limitations.

Keep the existing source-update protocol, dependencies, task data and credential storage compatible. Validate before publishing; report exact completed scope and remaining limits to the owner.

## 0.2.2 progress

Selected-channel history, last-24h counts within the sample, explicit sample-cap warning, bounded storage and improved save-error handling implemented. These are overlapping sample snapshots, not a complete measurement of server activity. Full historical collection and Discord voting remain pending.

## 0.2.3 progress — Activity System

Bounded 24h paging up to 500 messages, early stop, explicit coverage state and targeted permissions errors implemented. Empty responses do not prove zero activity. Cap, inaccessible/deleted messages and Voice activity remain limitations. Historical snapshots retain coverage metadata. Next: participation suggestions, then reviewed Lobby Night voting.

## 0.2.4 progress — Activity System

Explainable local participation suggestions with editable/copyable drafts implemented. Fresh confirmed capture required for activity-specific ideas; otherwise general ideas only. No automatic publishing or paid AI calls. Next: reviewed Discord voting for Lobby Night.

## 0.3.0 progress — Lobby Night

Native polls after explicit preview, durable delivery status, link copying and on-demand result reading implemented. No scheduled Discord events. Local cancellation does not remove a published poll. Unclear sends require manual verification; no background resending. Explicitly confirmed timed poll publication is implemented with persistent schedules, cancellation, a matching-server guard and no sends after the night begins. App must remain running and connected; missed publication can catch up only before the event. Scheduled Discord reminders remain pending. Next: Dashboard visibility and schedule recovery feedback, then Creator Hub.

## 0.3.1 progress — Lobby Night visibility

Schedule recovery feedback and aggregate publication counters are integrated into the existing Dashboard. Future/due/expired/canceled schedules are distinguished using the dispatcher’s actual deadline rules; ambiguous sends require manual inspection. Offline status refresh performs no Discord requests. This supports Lobby Night operations, rather than advancing the full Dashboard stage ahead of Creator Hub. Next: Creator Hub usability and permission prerequisites.

## 0.3.2 — professional overview requested by owner

Visual refinement of the existing shell and overview: grouped navigation, consistent theme, direct entries to Activity/Lobby Night/Creator Hub, real local open-task and upcoming-night previews. Does not introduce new analytics, live sources or change the authorized module order. Next functional stage remains Creator Hub.
