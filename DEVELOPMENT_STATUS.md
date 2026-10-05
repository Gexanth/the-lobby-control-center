# Development status — 0.3.3

Community access hotfix from 0.2.5 retained: all tabs navigable offline with local server context; live actions require matching Discord connection. GitHub Actions installs the existing application requirements and runs offscreen UI regressions.

Roadmap stage: Lobby Night. Native Discord polls can now be published from a saved future night after a concrete preview including target channel, time, options, duration and multiselect. Only normal text channels are supported. Mention parsing is disabled; no Discord scheduled event is created. Poll text limits and duplicate options validated. A persistent delivery journal is saved before sending, blocks repeated sends, records confirmed message IDs and retains ambiguous attempts after restart. Unclear attempts require explicit manual target-channel inspection before user reset; there is no guaranteed exactly-once delivery after network failures. Server-side nonce adds short-term duplicate suppression.

Poll links are copyable; results load on demand without voter/member enumeration. Missing results are unknown, not zero votes. Counts may be provisional until finalized. Local cancellation does not delete a published poll. Reminders remain local and require the app running.

Explicitly approved publication schedules are persisted with the exact reviewed payload. The one-minute dispatcher only sends while connected to the matching server and idle; it revalidates the saved plan before sending. Schedules can be stopped. Canceled or expired nights never send; a missed publication may catch up only before the night begins. This is desktop scheduling, not a hosted service. Unclear attempts stay blocked across restarts.

Validation: 37 tests covering real UI cancel/confirm flow with fake transport, offline access, same-server binding, publication state, wrong-server prevention, save-failure rollback, option limits, duplicate prevention, unknown results, scheduled dispatch without duplicate sends, schedule persistence/cancellation/expiry and prior credentials/activity/updater paths. No real Discord writes or paid API calls executed. Native Discord behavior still requires user confirmation on an actual server.

0.3.1 refinement: the Dashboard shows actual planned/due/published polls and warns about expired/canceled plans or ambiguous sends. Selected schedules explicitly distinguish future, due, canceled and expired states; a minute tick updates this feedback even offline. Publish controls stay disabled for canceled/past nights. No additional requests or stored data introduced.

Next: Creator Hub usability and validated Discord integration prerequisites; do not invent stream status sources. No new runtime dependencies or launcher protocol change.

0.3.2 — explicitly requested professional software overview: new card-based dashboard, grouped sidebar, uniform dark theme, clear focus/disabled states and checkbox indicators. Upcoming nights exclude canceled/past events; task count/preview uses local open tasks. Server values clear on disconnect while local work remains visible. Labels display plain text, not user-provided HTML. Overview shortcuts preserve page indices and Ctrl+1–8 bindings. Rendering inspected at 1280×1020 and 1180×760; the latter scrolls vertically without horizontal clipping. 33 tests include navigation and connection/local-state regressions. No server writes, data migration, new dependencies or starter changes.

Roadmap: presentation support for Activity/Lobby Night/Creator Hub at the owner’s request; full Dashboard analytics remains after Creator Hub. Next: Creator Hub workflow usability.

0.3.3 — Creator Hub workflow: split searchable/filterable list and editing form, actual status totals, keyboard selection, new-record action, saved-link copying and confirmed removal. Editing uses the selected immutable record ID, so changing a channel link does not duplicate the creator; collisions and cross-server edits are rejected. Legacy save-by-link callers remain compatible. Failed saves/removals roll back in-memory state. Refresh preserves an unsaved draft; changing server clears the editor and filters to prevent wrong-server edits. Data format remains 1 and existing fields/IDs are retained. 37 passing tests including edit/collision/server guards, rollback, filtering, drafts, clipboard and remove confirmation; no Discord/API calls.

Next Creator Hub step: optional Discord identity/role association with concrete preview and permission checks. Stream notifications require an explicitly configured verified source and are not implemented.
