## 0.4.12 — Quellenprüfung und nachvollziehbare Aufgaben

Roadmap stage: AI server analysis. Responses now display local ACT reference
lookups against the exact request snapshot; unknown references and absent ACT
citations are disclosed. Known sources show channel, capture time, sample counts,
coverage and quality. This validates lookup only, never factual correctness.
Up to ten distinct references are shown; additional references are disclosed.
When selected text lies within one assistant response, task review includes
editable provenance (server, request time, references and original sample data).
Selections spanning messages are not attributed automatically. Existing task
format, manual editing, cancel and failed-save retry remain unchanged.
Chat writes always append, fixing replacement of selected previous text during
new responses. Response positions use Qt cursor offsets, including emoji.
Source snapshots are session-local and cleared with the conversation/provider
change; only reviewed task notes persist. No new dependencies or permissions,
no real Discord mutation and no paid model request. Next: per-recommendation
review that distinguishes source lookup from whether a claim is supported.

## 0.4.11 — Analyseaktionen direkt erreichbar

Visual verification found that the shared Community tab height can push controls
below the viewport. Move analysis refresh/start actions above the evidence and
bound its height to 420 pixels; long evidence remains internally scrollable.
The current analysis actions are now reachable without scrolling at 1280x900.
This is an AI server analysis usability follow-up to 0.4.10.

Publication verified 2026-10-09: v0.4.10 run 37969916329 succeeded. Cumulative
v0.4.11 passed all 104 tests locally and in CI with Qt, zero skips (run
37970094314, job 113954219534). Latest release targets
3f1019aa6a0864ec1a25d5bfb1bb455821b88905. Uploaded assets: release.json
(288 bytes), ZIP (113152 bytes), ZIP SHA256
d323235786c79a0b8c8864670f06f81d572ec259f67623ae9cd90f1526a7dacc.
Local compile and update-package build also passed. Actual UI screenshot uses
isolated, explicitly labeled test data. No real Discord mutation or paid AI call.
https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.4.11

## 0.4.10 — Datengrundlage vor der KI-Analyse

Roadmap stage: AI server analysis, built on Activity System snapshots. The
Serveranalyse tab now previews bounded local activity evidence before any API
call, including timestamps, coverage, quality, withheld invalid/future counts,
and instructions to refresh weak data. Works offline; refreshes on tab entry,
server switch and explicit refresh. No new Discord request or permissions.
Each measurement has a deterministic ACT source identifier shared by preview
and AI context; current samples are included even without history. Identifiers
remain stable as samples age. The prompt asks for citations, but model citation
correctness is not automatically verified. No paid model call was made.
Raw duplicate activity samples are omitted when canonical evidence exists,
preventing invalid values bypassing withholding. Other context (server structure,
planned night fields, creator status counts) is disclosed below the preview.
No storage migration, dependency, credential or starter change. Next: reviewed
recommendation provenance and explicit handling of unknown AI source references.

## 0.4.9 — Aufgabenentwurf bei Speicherfehler behalten

AI assistant follow-through reliability: after a failed task write, reopen the
same editable review with title/details/status retained and clear retry feedback.
Nothing is marked saved after failure; cancel remains possible. This preserves
the draft during this dialog session, not across app termination. Regression
verifies same dialog, edited content retained and no task created on failure.

Publication verified 2026-10-09: v0.4.8 was first published via successful run
37968682972. Cumulative v0.4.9 then passed all 100 tests with Qt locally and in
CI, zero skips, run 37968892509. Release targets
11970efcf3cd6caa7654de9bc82e5d1471983fc9; release.json (285 bytes) and ZIP
(110965 bytes) are uploaded. No real Discord mutation or paid API test.
https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.4.9

## 0.4.8 — Empfehlungen als überprüfbare Aufgaben

Roadmap stage: AI assistant / server analysis follow-through. Explicitly selected
assistant text now opens an editable local review: concrete task, details and
status. Cancel writes nothing. The selected text initially fills the details;
the first line suggests a short task title. Empty title / >8000 detail characters
cannot save. Existing open tasks with identical title/details are not duplicated.
After the modal dialog, a newly started worker blocks a stale save. TaskStore
adds text/details/status atomically using the existing format and defaults.
No automatic Discord action, additional API call, credential/dependency/launcher
change. This is user-reviewed text, not an assertion that AI advice is verified.

Validation: all 99 tests passed locally with Qt and zero skips, including cancel,
edited persistence, status, duplicate prevention, length validation and busy guard.
Next: evidence-aware recommendation review and clearer task provenance while
preserving manually edited tasks; real paid-model output remains untested.

## 0.4.7 — Verlauf, belegte Analyse und Update-Zuverlässigkeit

Dashboard stage: selectable local channel history, latest 12 overlapping 24h
snapshots, capture time, counts, freshness and coverage. Invalid/future values
are withheld. No summed totals or invented trends. Upcoming nights now include
poll delivery state; community summary breaks down creator applications/status.

AI analysis stage: bounded whitelisted history evidence (50 channels / 12 points)
with generated time, quality and limitations. No message content, member identity,
creator notes, stream credentials or journal sent. Analysis entry explicitly asks
for sourced observations, gaps and justified next steps; fewer than three findings
are acceptable when evidence is absent. Both providers reject channel plans in
analysis-only mode. Real paid-provider quality remains unverified; no paid calls.
Assistant usability: explicitly selected response text can be saved as a local
task (4000-character limit), without executing it. Existing reviewed actions remain.

Owner-reported auto-download investigation found six-hour checks and a busy
worker skipping a due check until the next interval. Checks now run every 30 min;
busy checks retry each minute, failures after 5 min. Update page shows next check
and saved opt-out/launcher requirements. Startup activation/SHA256/dependencies,
credentials and saved tasks remain compatible. This fixes code paths; user's
actual local failure is not confirmed without their runtime error/status.

Next: inspect provider-produced analysis with owner credentials and refine
per-finding task preparation; avoid pretending the assistant has full server data.

Confirmed 2026-10-09 publication: run 37961065111 succeeded; all 98 tests
executed locally and in CI with Qt, zero skipped. Release v0.4.7 targets
bdd873e3c3b791698203b31954207baf612e8c94. Assets release.json (285 bytes)
and source ZIP (108635 bytes) uploaded with SHA256 digests. Screenshot
The-Lobby-0.4.7-Verlauf.png is the real UI with isolated example snapshots.
Also fixed 0.4.6 attention-empty label lifetime/layout retention, verified after
event processing. No actual server write or paid AI request used.
https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.4.7

## 0.4.6 — Dashboard: priorisierte Aufmerksamkeit

Neue Karte direkt unter dem Verbindungsstatus: unklare Abstimmungs-/Stream-
Sendungen, fällige und gestoppte Veröffentlichungspläne, Stream-Prüfprobleme,
gestoppte Sitzungsüberwachung, veraltete/begrenzte/ungültige Kanalstichproben und
offene Creator-Bewerbungen. Jeder Hinweis öffnet den passenden Community-Tab.
Die Reihenfolge priorisiert Versandklärung vor fälligen Aktionen und Routine.
Bestehende Qualitäts-/Terminregeln werden wiederverwendet; kein Netzwerkzugriff,
keine automatische Änderung und keine neue Speicherung. Unveränderte Hinweise
behalten ihre Widgets. Leere Daten bestätigen keine vollständige Serverprüfung.
Annahme: Hinweise gelten für den lokal ausgewählten Server; pausierte Quellen
sind bewusste Einstellungen und werden nicht als Fehler behandelt.

Nächster Schritt: Dashboard-Verlaufsübersicht mit sichtbarer Datenabdeckung,
danach die KI-Serveranalyse. Daten, Abhängigkeiten und Starter bleiben kompatibel.

Validation/publication 2026-10-09: all 93 tests passed locally and in GitHub CI
with Qt, zero skipped. Run 37959865953 succeeded. Release v0.4.6 targets
2fa5b8c86e964da3e7d52ec0e2f936bfc7659cca; release.json (285 bytes) and ZIP
(104037 bytes) are uploaded with SHA256 digests. Actual screenshot uses isolated
local example records, no Discord connection or paid API request. Release:
https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.4.6

## 0.4.5 — Dashboard: reale Stream-Gesundheit

Die Dashboard-Stufe beginnt mit einer operativen Stream-Übersicht. Für den lokal
ausgewählten Server zeigt sie eingerichtete, aktive und pausierte Quellen, den
Sitzungszustand der Überwachung, aktuelle/fällige/noch nie geprüfte Quellen sowie
bestätigte und unklare Versandversuche. Grundlage sind ausschließlich die aktuelle
Creator-Konfiguration und das bestehende lokale SQLite-Protokoll. Die Übersicht
öffnet Creator Hub direkt und aktualisiert sich bei Zustandsänderungen.

Der Dashboard-Leseweg öffnet ein vorhandenes Protokoll schreibgeschützt und legt
bei einem neuen Server keine Datei an. Er führt keine Twitch-, YouTube- oder
Discord-Anfrage aus, startet keine Überwachung und zeigt keine erfundenen Live-
oder Aktivitätswerte. Historische Versandzahlen bleiben nach Entfernen eines
Creators absichtlich erhalten. 89 Tests passieren mit Qt und ohne übersprungene
Tests, darunter Server-Isolation, fällige/ungeprüfte/fehlerhafte Abrufe, unklare
Versandreservierungen, read-only Verhalten und die tatsächliche Dashboard-Anzeige.
Keine echte Discord-Änderung und kein bezahlter API-Aufruf.

Bestätigte Veröffentlichung am 09.10.2026: GitHub-Actions-Lauf 37939527364
endete erfolgreich und führte alle 89 Tests mit Qt ohne Überspringen aus. Release
v0.4.5 zeigt auf Commit ff71ee3b950449b55ff639958d45d5aa3a4dcec9;
`release.json` (285 Bytes) und das Quell-Update-ZIP (101.211 Bytes) sind mit
GitHub-SHA256-Digests hochgeladen. Release:
https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.4.5 . Die
echte Vorschau `The-Lobby-0.4.5-Dashboard.png` verwendet ausschließlich isolierte
lokale Beispieldaten und keine Discord-Verbindung.

Nächster Dashboard-Schritt: die vorhandenen Activity-, Lobby-Night- und Creator-
Zustände zu einer klaren Aufmerksamkeitsliste zusammenführen. Erst danach folgt
die KI-Serveranalyse auf diesen belegten lokalen Grundlagen.

## 0.4.4 — Fair polling order

Final multi-creator review found that a fixed list scan could repeatedly select the
first two Twitch sources at two-minute intervals and starve later creators. Pick
the never-checked/oldest-checked due source first. Added a UI regression where an
already-due first creator must yield to a never-checked second creator. 87 tests
pass with Qt and zero skips. Same opt-in and credential requirements as 0.4.3.

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

## 0.4.1 — Claude provider integration

User-requested integration alongside the roadmap: Claude / Anthropic is the
initial provider in Settings; OpenAI remains supported. Provider-specific session
keys/models, provider-switch history/plan reset, German errors, and forced
single-plan Anthropic tool output reuse the existing validated preview flow.
No Discord writes or paid API requests were made during development. Keys are
never written to project files. Real API/account/model availability remains to be
verified with the user's own key. No added runtime dependency or updater change.

Validation: 68 tests passed locally, zero skipped, including provider payload,
authentication headers, context whitelist, truncated/ambiguous/invalid responses,
OpenAI compatibility, and UI provider/key/history isolation and dispatch.

# Development status — 0.4.0

0.4.0 — Lobby Night proposal review and safe draft editing. The local planner validates the same option limits needed by Discord before saving: 2–10 non-empty, case-insensitively unique suggestions, each at most 55 characters. Live readiness feedback shows option count and local event time. Selecting a saved plan loads its title/time/options back into the form, shows a numbered review summary, and allows ID-preserving edits without creating duplicates. Editing resets the local reminder for the changed future time. Canceled nights and poll deliveries in scheduled/sending/uncertain/sent states are locked; the existing explicit Discord publication preview remains mandatory. Storage failure restores the prior draft. Existing records/data format remain compatible.

Confirmed publication on 2026-10-08 at 15:30 Europe/Berlin: workflow run 37784768055 completed successfully. CI initialized Qt and reports all 60 tests passed with the no-skips guard. Release v0.4.0 targets commit 0f9fe4a3283bc3c1c85e804750480bd88f08b910. Uploaded assets: release.json (285 bytes) and source ZIP (80,006 bytes), both with GitHub SHA256 digests. Release: https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.4.0 . Actual screenshot The-Lobby-0.4.0-Lobby-Night.png uses isolated local example data and no Discord connection; it shows readiness, editing and the explicit “no Discord event” review summary.

Scope assumption: suggestions are entered manually from owner/team decisions. The app does not read proposal-channel message content, infer community choices, create a Discord scheduled event or automatically publish while drafting. Discord requests still happen only in the existing explicitly reviewed native-poll flow. No new dependency, credential, task, starter or updater change.

Validation: all 60 tests passed locally with PySide6 and offscreen UI, zero skipped. New regressions cover early duplicate/length validation, normalized whitespace, safe edit preserving identity, reminder reset, delivery-state lock, disk-write rollback, live UI readiness, single-record update and returning to a clean new draft. No real Discord request/write, paid API call or fabricated proposal data used. Compilation plus source ZIP/manifest/SHA256 verification required before publication.

Next ordered-roadmap step: continue Lobby Night automation with a clearer publication/readiness summary and local reminder controls, still without Discord scheduled-event creation. Creator Hub follows after this stage; Dashboard and AI server analysis remain later.

0.3.9 — Activity System permission/setup feedback: the Activity page now states the exact read-only channel prerequisites (View Channel / Kanal ansehen and Read Message History / Nachrichtenverlauf anzeigen); Send Messages is not required. Sanitized Discord 403/404 guidance is endpoint-specific, so a blocked channel lookup is distinguished from a blocked message-history request without reading or exposing Discord response bodies, headers or tokens. A successful capture visibly confirms access. A permission failure keeps existing samples untouched and turns off the optional 15-minute auto-capture to avoid repeated failing requests; transient network/rate-limit failures do not disable it. No extra Discord request, server write, stored permission data, dependency, launcher or updater change.

Confirmed publication on 2026-10-07 at 15:45 Europe/Berlin: workflow run 37631011470 completed successfully. The release validation initialized Qt and reports all 57 tests passed; the workflow's no-skips guard also passed. Release v0.3.9 targets commit 03fd8ab16f5559369f934fb8cee5e576493337bf. Uploaded assets: release.json (285 bytes) and the 77,582-byte source ZIP, both with GitHub SHA256 digests. Release: https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.3.9 . Actual screenshot The-Lobby-0.3.9-Rechtehilfe.png uses isolated fake transport and illustrates the permission failure; no live Discord request or invented activity data.

Validation: all 57 tests passed locally with PySide6 and the offscreen UI, zero skipped. New regressions cover endpoint-specific sanitized guidance, permission-failure display, stopping auto-retry, no sample mutation and successful-access confirmation. Compilation and source ZIP/manifest/SHA256 checks are required before publication. No real Discord connection/write or paid API request used. Runtime requirement for capture: bot membership plus View Channel and Read Message History in the selected text/announcement channel; Discord role/channel overwrites decide the effective permissions.

Next ordered-roadmap step: Activity System capture-readiness feedback is now complete at the available REST-error level. Continue with the existing Lobby Night stage by making proposal collection and poll preparation easier to review, without creating a Discord scheduled event. Creator stream sources, full Dashboard analytics and expanded AI analysis remain later stages.

0.3.8 — release validation hardening: review of the successful 0.3.7 workflow logs revealed 21 Qt-dependent tests skipped on the runner despite installing PySide6. All 54 tests had actually executed and passed locally. The workflow now installs Linux EGL/OpenGL runtime libraries, explicitly imports/initializes Qt and application modules, and refuses publication if any test is skipped. This changes only CI infrastructure, not Windows dependencies, starters, saved data or source updater. Cumulative package retains the 0.3.7 Activity freshness improvements and 0.3.6 reviewed deletion. Actual 0.3.8 publication outcome must be verified.

Confirmed 0.3.8 publication, 2026-10-06 15:25 Europe/Berlin: run 37470594729 completed successfully. Its logs confirm Qt initialization and all 54 tests executed and passed, with zero skipped. Release v0.3.8 targets 8bfed4ebd0d2593033edcadc585a8b9eaf908168; release.json (285 bytes) and source ZIP (75,712 bytes) are uploaded. Release: https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.3.8 . Local compile/build/manifest/checksum validation also passed. Actual screenshot The-Lobby-0.3.8-Activity.png shows the empty offline native page; it contains no fabricated server measurements. Next iteration starts from this confirmed release and the Activity permission/setup feedback task below.

0.3.7 — Activity System freshness: explicitly label counts as the 24h before the stored capture, with capture date/time. Separate current, older-than-six-hours, limited/unconfirmed, invalid and future-dated feedback. Reuse one quality classifier for activity feedback and local participation suggestions. Existing minute timer updates freshness and falls back to general ideas when a snapshot ages, even offline, without additional Discord/API calls. Edited drafts are retained; unchanged history cells are reused. Invalid timestamps/counts never drive inactivity recommendations. Saved snapshots/settings/tasks/credentials and data format are unchanged. No new dependencies or starter/update-protocol changes.

Validation: all 54 tests passed with PySide6 installed and offscreen UI enabled, including six-hour boundary, malformed/future captures, unconfirmed empty data, timer aging without requests, draft preservation, unchanged history cells and all deletion/roles/polls/updater regressions. No real Discord server writes or paid requests. Screenshot is the actual empty offline Activity page, without invented activity. Source compilation and local ZIP/manifest/checksum checks completed before publication.

Publication recovery: 0.3.6 commit remains in main, but its release job was cancelled without a runner or any executed steps; latest published release at start of this iteration was 0.3.5. The unchanged release workflow is retriggered by the 0.3.7 version bump; this package also includes the tested 0.3.6 deletion feature. Actual release outcome must be checked separately; do not claim availability from a commit alone.

Confirmed publication on 2026-10-06 at 15:21 Europe/Berlin: workflow run 37470127466 completed successfully, but log review found 21 skipped Qt tests; local validation did execute all 54. Release v0.3.7 targets commit 00454f0c2dbad41c2d8bc4f75cdfd044544f7780 and both release.json and the 75,080-byte source ZIP are uploaded. Release: https://github.com/Gexanth/the-lobby-control-center/releases/tag/v0.3.7 . The prior 0.3.6 publication failure is resolved by this cumulative release. Activation remains the next start.bat launch; EXE updating remains unsupported.

The permission/setup feedback named here was completed in 0.3.9.

Community access hotfix from 0.2.5 retained: all tabs navigable offline with local server context; live actions require matching Discord connection. GitHub Actions installs the existing application requirements and runs offscreen UI regressions.

Roadmap stage: Lobby Night. Native Discord polls can now be published from a saved future night after a concrete preview including target channel, time, options, duration and multiselect. Only normal text channels are supported. Mention parsing is disabled; no Discord scheduled event is created. Poll text limits and duplicate options validated. A persistent delivery journal is saved before sending, blocks repeated sends, records confirmed message IDs and retains ambiguous attempts after restart. Unclear attempts require explicit manual target-channel inspection before user reset; there is no guaranteed exactly-once delivery after network failures. Server-side nonce adds short-term duplicate suppression.

Poll links are copyable; results load on demand without voter/member enumeration. Missing results are unknown, not zero votes. Counts may be provisional until finalized. Local cancellation does not delete a published poll. Reminders remain local and require the app running.

Explicitly approved publication schedules are persisted with the exact reviewed payload. The one-minute dispatcher only sends while connected to the matching server and idle; it revalidates the saved plan before sending. Schedules can be stopped. Canceled or expired nights never send; a missed publication may catch up only before the night begins. This is desktop scheduling, not a hosted service. Unclear attempts stay blocked across restarts.

Validation: 51 tests covering real UI cancel/confirm flow with fake transport, offline access, same-server binding, publication state, wrong-server prevention, save-failure rollback, option limits, duplicate prevention, unknown results, scheduled dispatch without duplicate sends, schedule persistence/cancellation/expiry and prior credentials/activity/updater paths. No real Discord writes or paid API calls executed. Native Discord behavior still requires user confirmation on an actual server.

0.3.1 refinement: the Dashboard shows actual planned/due/published polls and warns about expired/canceled plans or ambiguous sends. Selected schedules explicitly distinguish future, due, canceled and expired states; a minute tick updates this feedback even offline. Publish controls stay disabled for canceled/past nights. No additional requests or stored data introduced.

Next: Creator Hub usability and validated Discord integration prerequisites; do not invent stream status sources. No new runtime dependencies or launcher protocol change.

0.3.2 — explicitly requested professional software overview: new card-based dashboard, grouped sidebar, uniform dark theme, clear focus/disabled states and checkbox indicators. Upcoming nights exclude canceled/past events; task count/preview uses local open tasks. Server values clear on disconnect while local work remains visible. Labels display plain text, not user-provided HTML. Overview shortcuts preserve page indices and Ctrl+1–8 bindings. Rendering inspected at 1280×1020 and 1180×760; the latter scrolls vertically without horizontal clipping. 33 tests include navigation and connection/local-state regressions. No server writes, data migration, new dependencies or starter changes.

Roadmap: presentation support for Activity/Lobby Night/Creator Hub at the owner’s request; full Dashboard analytics remains after Creator Hub. Next: Creator Hub workflow usability.

0.3.3 — Creator Hub workflow: split searchable/filterable list and editing form, actual status totals, keyboard selection, new-record action, saved-link copying and confirmed removal. Editing uses the selected immutable record ID, so changing a channel link does not duplicate the creator; collisions and cross-server edits are rejected. Legacy save-by-link callers remain compatible. Failed saves/removals roll back in-memory state. Refresh preserves an unsaved draft; changing server clears the editor and filters to prevent wrong-server edits. Data format remains 1 and existing fields/IDs are retained. 37 passing tests including edit/collision/server guards, rollback, filtering, drafts, clipboard and remove confirmation; no Discord/API calls.

Next Creator Hub step: optional Discord identity/role association with concrete preview and permission checks. Stream notifications require an explicitly configured verified source and are not implemented.

0.3.4 — Creator Hub role linking: explicit local member/role ID mapping for saved creators. Accepted creators can request a live read-only preview, then confirm a single role assignment. Bot identity/membership, target human membership, guild, Manage Roles/Administrator and strictly lower target-role position are freshly checked before preview and again before PUT. Supports only existing non-managed roles with zero guild permission bitfield, retaining the prior adapter restriction; channel overwrites may still give role-specific access. Already-present roles send no write. PUT adds only the selected role; it does not replace others. Confirmed membership is read back after assignment. Delivery intent is persisted before writes; unclear attempts remain visible across restarts and are never auto-retried. Every later attempt first reads current membership. Local mutations are blocked during the job. Linking/removal/status changes do not revoke existing roles. IDs remain local and are excluded from AI creator context.

Validation: 51 tests passed, including fake-transport permission/hierarchy/managed/privileged-role guards, changed preview, disabled writes, existing-role no-op, persistence rollback, UI cancel/confirm, unclear failure and failed intent save preventing writes. No real Discord server changes or paid API calls. Live Windows/Discord assignment still needs the owner’s runtime confirmation. No requirements/launcher/data-format changes.

Next: role selection from loaded server overview and verified stream-source configuration; automatic stream announcements are still pending.

0.3.5 concurrency refinement: modal confirmation dialogs process Qt timer events. Recheck worker availability and client identity after role confirmation, before persisting delivery intent; refuse poll dispatch when another job has started. Prevents a stale sending record when run_discord_job would decline a concurrent action. The UI role regression explicitly simulates a job starting during confirmation; all 44 tests pass.

0.3.6 — owner-requested channel/category deletion: new delete action in Discord → Manage channels and structured AI planning. Existing server-channel IDs only; types text/voice/category/announcement/stage/forum/media supported, no DMs/threads/bulk deletion. Fresh same-guild/target identity and protected Community channel checks. Category preview lists all child names/IDs and explicitly retains them; snapshot changes require fresh review. Scrollable plain-text destructive confirmation requires exact target ID. No deletion from AI response alone. Rechecks worker/client after modal confirmation; response must confirm target ID. Uses the existing audited, write-gated DELETE route, then refreshes the overview. No automatic retry or Discord undo; local backup does not restore server content. Local task/community/credential data retained.

Validation: 51 tests passed, including fake-transport category single-target delete retaining children, ordinary channel delete, changed snapshot, foreign/protected targets, disabled writes, AI target/field validation, exact-ID dialog and modal concurrency guard. No actual Discord delete or paid AI request executed. New UI screenshot uses isolated example data. Requirements, source-update protocol and starters unchanged.

Roadmap: this requested server-management/AI capability is additional to the ordered community roadmap; next planned Creator Hub step remains easier role selection and verified stream-source setup.

