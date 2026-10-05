# Development status — 0.3.0

Community access hotfix from 0.2.5 retained: all tabs navigable offline with local server context; live actions require matching Discord connection. GitHub Actions installs the existing application requirements and runs offscreen UI regressions.

Roadmap stage: Lobby Night. Native Discord polls can now be published from a saved future night after a concrete preview including target channel, time, options, duration and multiselect. Only normal text channels are supported. Mention parsing is disabled; no Discord scheduled event is created. Poll text limits and duplicate options validated. A persistent delivery journal is saved before sending, blocks repeated sends, records confirmed message IDs and retains ambiguous attempts after restart. Unclear attempts require explicit manual target-channel inspection before user reset; there is no guaranteed exactly-once delivery after network failures. Server-side nonce adds short-term duplicate suppression.

Poll links are copyable; results load on demand without voter/member enumeration. Missing results are unknown, not zero votes. Counts may be provisional until finalized. Local cancellation does not delete a published poll. Reminders remain local and require the app running.

Explicitly approved publication schedules are persisted with the exact reviewed payload. The one-minute dispatcher only sends while connected to the matching server and idle; it revalidates the saved plan before sending. Schedules can be stopped. Canceled or expired nights never send; a missed publication may catch up only before the night begins. This is desktop scheduling, not a hosted service. Unclear attempts stay blocked across restarts.

Validation: 30 tests covering real UI cancel/confirm flow with fake transport, offline access, same-server binding, publication state, wrong-server prevention, save-failure rollback, option limits, duplicate prevention, unknown results, scheduled dispatch without duplicate sends, schedule persistence/cancellation/expiry and prior credentials/activity/updater paths. No real Discord writes or paid API calls executed. Native Discord behavior still requires user confirmation on an actual server.

Next: show scheduled publication status in the Dashboard and improve schedule recovery feedback; then Creator Hub integrations. No new runtime dependencies or launcher protocol change.
