# Community roadmap

Order authorized by the owner: Activity System → Lobby Night automation → Creator Hub → Dashboard → AI server analysis.

## 0.2.0: first integrated foundation

- Activity System: aggregate the last 100 messages in one selected text/announcement channel, excluding bots. Optional polling every 15 minutes while connected. Store counts, unique participant count and time range; never persist message content or author IDs. Samples are bounded, not complete server activity or trends.
- Lobby Night: local server-scoped date, suggestions and cancellation; copyable voting text; one-time app reminder at due time or next connection. No live Discord poll, event or outgoing message yet.
- Creator Hub: local Twitch/YouTube application records, accepted/paused status, editing and removal. No live status lookup, automatic roles or stream announcements yet.
- Dashboard: community counts for the connected server. Full charts and history pending.
- AI analysis: explicit analysis action uses the existing configured OpenAI connection; sends whitelisted aggregate samples, local event planning and creator status counts. No message content, bot credentials, creator names or links sent through this context. API response quality has not been tested against a live paid service.

## Next priorities

0.4.10 — AI server analysis: local evidence preview, stable per-measurement source
IDs, data-quality guidance and sanitized latest samples even without history.
Prompt requests source references; correctness is not yet mechanically checked.
Next: validate references and preserve provenance during reviewed task creation.

0.4.9 — AI assistant task reliability: retain edited review during save failures;
retry or cancel without losing the current dialog contents. No new data format.

0.4.8 — AI assistant follow-through: editable task review for selected suggestions,
with details/status and open-task duplicate prevention. This follows the existing
Dashboard/evidence foundation. No autonomous action or new server data source.
Next: evidence-aware recommendation review and task provenance.

0.4.7: Dashboard history/coverage and unified night/creator status implemented.
AI server analysis now receives bounded local evidence and rejects action plans
from the analysis entry. Selected recommendations can become local tasks.
Assumption: histories are overlapping snapshots, never full-server trends or
growth. No live provider test or autonomous Discord change. User-reported update
delay also addressed through 30-minute checks and busy/error retry scheduling.
Next: evidence quality and per-recommendation workflow refinement.

0.4.6 Dashboard progress: prioritized local attention list with direct Community
navigation implemented. Ambiguous sends, due/stopped polls, stream errors/stopped
session, activity quality and open applications use existing stored evidence.
No network request or live server mutation. Next: actual history/coverage overview,
then AI server analysis; authorized module order remains unchanged.

1. Activity history and consistent time windows, permissions feedback and participation prompts.
2. Reviewed Discord voting-message integration, delivery records and reminders that avoid duplicates. Always clarify whether scheduling depends on the desktop app remaining connected. Actual Discord event creation was previously withdrawn.
3. Creator workflows integrated with Discord roles and verified live-stream sources.
4. Dashboard trends based on real history, no invented metrics.
5. Expanded AI recommendations with evidence and sample limitations.

Keep the existing source-update protocol, dependencies, task data and credential storage compatible. Validate before publishing; report exact completed scope and remaining limits to the owner.

## 0.4.5 — Dashboard: Stream-Betriebszustand

Die vierte Roadmap-Stufe beginnt mit einer serverbezogenen Stream-Karte im
Dashboard. Sie fasst nur gespeicherte Creator-Konfiguration und das vorhandene
lokale Prüf-/Versandjournal zusammen: aktiv/pausiert, Sitzungsüberwachung,
aktuell/fällig/ungeprüft/fehlerhaft sowie bestätigt/unklar versendet. Ein direkter
Weg führt zurück in den Creator Hub. Das Lesen ist lokal und schreibgeschützt;
ohne Journal wird keine Datenbank erzeugt. Es gibt keine zusätzliche Anbieter-
oder Discord-Anfrage und keine Behauptung eines dauerhaft laufenden Dienstes.

Nächster Schritt derselben Dashboard-Stufe: echte vorhandene Warnzustände aus
Activity System, Lobby Night und Creator Hub priorisiert zusammenführen. Danach
folgt die KI-Serveranalyse, ausschließlich mit belegten Daten und sichtbaren
Einschränkungen.

## 0.3.7 — Activity System reliability

Returned to the first roadmap stage for a concrete accuracy gap: stored measurements now show their capture timestamp and explicitly refer to the 24h before that capture. Current, stale (>6h), limited/unconfirmed, invalid and future-dated measurements are distinguished. Existing minute timer refreshes age feedback and participation recommendations without new requests; edited drafts and historical snapshots remain intact. An unconfirmed empty response is not displayed as a reliable zero. No fabricated activity or new sources. Runtime for new captures remains a connected bot with View Channel and Read Message History in the selected channel; local feedback also works offline.

Next: clear permission/setup guidance using actual capture errors. Then continue Lobby Night → Creator Hub → Dashboard → AI analysis in the authorized order. Existing later-stage foundations are retained.

## 0.3.8 — validation supporting every roadmap stage

Linux Qt runtime prerequisites and mandatory UI import/initialization added to release CI. Publication now blocks on skipped tests, so Activity/Lobby Night/Creator Hub UI regressions must actually execute. No functional roadmap reorder, Windows dependency change or live Discord test introduced.

## 0.3.9 — Activity System permission readiness

The page now names the exact read-only channel prerequisites and turns actual 403/404 capture failures into endpoint-specific setup help. A successful capture confirms access. Permission failures stop optional 15-minute retrying and do not overwrite prior samples; no additional permission probe or stored permission inventory is introduced. This completes the currently scoped Activity setup-feedback step using only real request outcomes. Required at runtime: bot in the server, View Channel and Read Message History for the selected text/announcement channel; Send Messages is not needed.

Next ordered step: improve Lobby Night suggestion collection and reviewed poll preparation. Continue to avoid Discord scheduled-event creation. Then Creator Hub → Dashboard → AI analysis.

## 0.4.0 — Lobby Night draft review

Local, manually entered game suggestions now receive live readiness feedback using Discord poll limits before saving. Saved drafts can be selected, reviewed and edited without changing their identity or creating duplicate plans. Canceled nights and scheduled/in-flight/unclear/published poll deliveries are locked. This deliberately does not ingest proposal-channel messages, create Discord scheduled events or publish a draft automatically. Existing reviewed native-poll preview, durable delivery journal and connected-desktop scheduling remain in place.

Next: improve Lobby Night publication/readiness summary and local reminder controls. Then resume Creator Hub work, followed by Dashboard and AI analysis.

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

## 0.3.3 — Creator Hub

Bewerbung/Angenommen/Pausiert filtering, search, status counts, explicit editing/new-record flow, safe ID-based link changes and confirmed removal implemented. Offline server-scoped records retained; no live roles or stream status claimed. Next: optional member/role mapping with reviewed permission-aware actions; stream notification sources still need configuration. Dashboard analytics and expanded AI analysis remain later stages.

## 0.3.4 — Creator Hub: reviewed role association

Optional member/role IDs stored locally; accepted creators can preview verified human member/role names and explicitly assign one existing role. Permission/hierarchy checks are refreshed immediately before execution, result read back, unknown delivery retained without auto-retry. Only non-managed roles with zero guild permission bitfield are supported; channel overwrites are not analyzed. Local status changes/removal never revoke roles. Stream notifications remain pending, require a configured verified source. Next: easier role selection and source setup.

## 0.3.5 — Creator Hub / Lobby Night concurrency

Confirmation-time worker/client guards prevent recording delivery intent for an operation blocked by another job. Role UI regression simulates timer activity during confirmation. Functional module order unchanged.

## 0.3.6 — owner-requested Discord/AI management capability

Reviewed single-channel/category deletion in the form and AI planning, with explicit target-ID confirmation and category child retention. No live deletion performed as test. This independent management request does not change Activity → Lobby Night → Creator Hub → Dashboard → AI analysis order. Creator role selection/source setup remains next.

## 0.4.2 — Lobby Night readiness and Creator review

User requested both roadmap areas together. Lobby Night now shows missing
publication prerequisites and durable per-night local reminder choices: at the
event, 15/30/60/1440 minutes before, or disabled. Existing records retain their
at-event reminder. Unchanged settings do not rearm a delivered reminder; changed
settings do. Reminders require the app running and the server selected; missed
reminders appear when selected again. This does not send Discord reminders.

Creator Hub adds private local review notes (2000 characters maximum) and a
saved-state next-step guide from application through binding and last-confirmed
role delivery. Notes survive edits and are excluded from the AI context. The guide
clearly states that automatic stream notifications still require setup in the
external bot; no live Twitch/YouTube detector or notification activation claimed.
The stale OpenAI-only analysis label now includes Claude.

Validation: 72 tests passed with Qt, zero skipped. New tests cover reminder time
boundaries, disable/reload/deduplication, validation/write rollback, note persistence,
role binding preservation, AI exclusion, and actual UI save/select/reset paths.
No real Discord mutation or paid AI request used. No new runtime dependencies.

## 0.4.3 — Optional native stream notifications

Creator Hub now resolves Twitch logins / YouTube handles or channel IDs against
fixed official API endpoints and stores immutable provider IDs with a Discord
destination. Default paused; read-only live check; explicit per-creator activation
preview and acknowledgment of other bots being disabled. Session monitoring starts
off, credentials remain session-only. Twitch validates tokens on each request cycle.
YouTube verifies actual live state after search. No role/Everyone mentions.

A separate SQLite journal atomically reserves each guild/provider/channel-identity/
stream identity before POST. Destination changes and creator removal never erase
deduplication. Sent, unfinished and uncertain reservations block repeat attempts;
Discord nonce adds a second short-term guard. Checks are also atomically throttled:
Twitch 120s, YouTube 1800s, maximum 80 YouTube searches per rolling 24h across the
installation. One due source checked per minute. Worker threads perform network
operations; local CommunityStore mutations remain on the UI thread. Worker is now
registered before busy-control refresh, so stream controls are disabled immediately.
Errors stop session monitoring. Status/source edits pause authorization. API response
bodies and credential-bearing URLs are not surfaced in errors.

Validation: 86 tests passed with Qt, zero skipped. Added fake-transport provider
identity/live/offline/ended checks, budget and restart boundaries, duplicate-source
and state rollback tests, at-most-once attempts across restart/channel changes/removal,
uncertain/wrong response/disk failure tests, and actual UI read-only/confirm/pause/
automatic dispatch flows. No real Discord write or paid API request executed.
Live Twitch/YouTube/Discord end-to-end operation still requires the owner's session
credentials and configuration. Existing historical MEE6 announcements were read;
no current MEE6 setup or disabling is claimed. No new Python dependencies.

Next: Dashboard integration showing actual recorded check/delivery health. Current
feature is desktop polling, not an always-on hosted service. External bots and other
independent installations are outside the local deduplication guarantee.

## 0.4.4 — Fair polling order

Final multi-creator review found that a fixed list scan could repeatedly select the
first two Twitch sources at two-minute intervals and starve later creators. Pick
the never-checked/oldest-checked due source first. Added a UI regression where an
already-due first creator must yield to a never-checked second creator. 87 tests
pass with Qt and zero skips. Same opt-in and credential requirements as 0.4.3.

