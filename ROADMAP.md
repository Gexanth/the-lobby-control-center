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
