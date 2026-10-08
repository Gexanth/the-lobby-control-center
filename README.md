# The Lobby Control Center

Discord control center with a Python/PySide6 desktop interface.

## Start on Windows

Install Python 3.12, extract the latest release ZIP, and open `start.bat`.
Keep the extracted folder as your permanent launcher folder.

## Automatic updates

From 0.1.6, fresh installations automatically check the official GitHub release
at startup and every six hours while running. Existing update preferences are
preserved. In Updates, enable automatic downloads and use:

https://github.com/Gexanth/the-lobby-control-center/releases/latest/download/release.json

Verified packages are activated at the next start through `start.bat`.
Tasks and settings are stored separately. Startup failures restore the previous
version; `restore_previous.bat` also provides manual recovery.

## Publish a version

Commit tested source changes to main and increase `VERSION` in `version.py`.
GitHub Actions validates the updater, builds the source ZIP and checksum
manifest, and publishes a versioned GitHub Release. Existing releases are never
overwritten. Workflow dispatch can retry a failed publication.

This pipeline distributes published changes; it does not develop new features.
EXE updates and changes requiring new dependencies need a full installation.

## Taskbar shortcut (Windows, 0.1.7)

Extract the complete 0.1.7 release into a permanent folder and run
`taskleisten_icon_einrichten.bat` once. It installs dependencies if needed and
creates desktop and Start menu shortcuts with a purple Lobby icon.
Search for The Lobby Control Center in Start, right-click and pin to taskbar.
The shortcut uses pythonw and the existing update launcher without a console.
Keep this folder in place. Existing users must extract this full release once
to place the new shortcut entry point in their permanent launcher folder.
Updates continue to activate on the next launch. Startup errors appear in a
dialog and diagnostics are retained in the user data directory startup.log.

## Saved Discord credentials (0.1.8)

On Windows, enable Remember credentials and connect successfully once. The bot
token is saved in Windows Credential Manager; only the server ID and preference
are saved in local settings. Credentials populate on the next launch. Use Delete
saved credentials to remove both stored values. Disconnecting ends the active
connection without deleting saved login details. No new dependencies required.

## Community workspace (0.2.0)

Connect Discord, then open Community. Activity System reads a selected channel
with up to 100 latest messages; requires View Channel and Read Message History.
Optional 15-minute sampling runs only while the app is connected. Lobby Night
provides local planning, copyable voting text and local reminders. Creator Hub
provides local application management. Dashboard shows stored community counts.
Server analysis uses your configured OpenAI API key on explicit request.
See ROADMAP.md for remaining Discord integrations and data limitations.

## Interface improvements (0.2.1)

Dashboard shows the last fetched member/online counts and channels, with direct
community shortcuts. The active sidebar section is highlighted. Ctrl+1 through
Ctrl+8 navigate between pages. Scrollable pages accommodate smaller windows.
Status bar shows the connected server and background operations. Activity polling
survives same-server overview refreshes; unchanged Creator/Night lists preserve
selection and are not rebuilt. Server metrics are snapshots, not live streaming.

## Activity history (0.2.2)

Community → Activity shows the selected channel and up to 96 historical samples.
Repeated checks within 15 minutes update one point. Old points expire after 30
days when a new sample is recorded. The 24h counts apply only to the latest 100
messages read and exclude bots. At the 100-message cap, counts may be incomplete.
History points overlap: do not sum them. Existing local data remains compatible.

## 24h activity coverage (0.2.3)

New captures read up to five pages / 500 messages per selected channel, stopping
when the 24h boundary or accessible history end is reached. The table shows
coverage: 24h reached, history end, cap reached or unconfirmed. An empty response
can mean an empty channel or missing Read Message History: do not interpret it
as confirmed zero activity. Stored older 100-message snapshots remain labeled.
No message contents or author IDs are stored; dependencies unchanged.

API reference: https://github.com/discord/discord-api-docs/blob/main/developers/resources/message.mdx

## Participation ideas (0.2.4)

Open Community → Mitmachimpulse or use the shortcut on Activity. Select an idea,
edit the draft and copy it into Discord if appropriate. Nothing is sent by the
app. Suggestions are local rules with visible reasons, not AI analysis. Old or
incomplete activity data only produces general ideas. No additional API calls.

## Community access (0.2.5)

Community tabs remain navigable before connecting. Choose or enter the server ID
and open local data for offline planning and stored records. Use the direct
Discord connection button for new activity captures and server analysis.
Disconnecting retains local data; live captures stay blocked until connected.

## Native Lobby Night poll (0.3.0)

Connect Discord, open Community → Lobby Night, save a future night and select it
in the list. Choose a normal text channel, poll duration and multiselect. Click
Review and publish, inspect the concrete preview and confirm to send. Bot needs
View Channel, Send Messages and Send Polls. Read Message History is needed for
result retrieval. Poll options must be unique and at most 55 characters each.
Published links are copyable and results can be loaded on demand. No scheduled
Discord event is created. Canceling a local night does not delete its poll.

Uncertain sends are never retried automatically. Inspect the target channel
before manually releasing a retry. Successful publication records the message
ID. No member or role pings are generated. Local reminders require the app open.

For automatic publication, enter a future local PC date/time before the night
and choose Review and schedule. Confirm the exact preview. The approved payload
and time survive restart; the app checks every minute while connected to the
matching server. Keep the app open and connected. A missed publication can catch
up before the night begins; canceled or expired nights never publish. Use Stop
scheduled publication to cancel. This does not create a hosted/background
service or automatic Discord reminder. Ambiguous attempts remain blocked.

API references: https://docs.discord.com/developers/resources/poll and
https://docs.discord.com/developers/resources/message#create-message

## Publication status (0.3.1)

The Dashboard shows planned, due and published poll counts from local delivery
records, with warnings for unclear sends and canceled/expired schedules. These
are delivery records, not a live server scan. Lobby Night displays the selected
schedule’s current status even offline. Canceled/past nights cannot start a new
publication. Stop a pending schedule to clear it; no Discord message is deleted.

## Professional overview (0.3.2)

The start page groups server metrics, open local tasks, upcoming Lobby Nights
and Community entry points into cards. Server metrics come from the most recent
Discord overview and clear on disconnect; local tasks and selected-server plans
remain available offline. Upcoming nights exclude canceled/past entries.
Grouped navigation preserves all existing page shortcuts (Ctrl+1–8).
The shared theme improves focus, disabled controls and checkbox visibility.
At shorter window heights the page scrolls vertically. No data migration or
additional network requests are introduced.

## Creator Hub workflow (0.3.3)

Select a local server under Community, then Creator Hub. Search by name/link or
filter by application status. Select an entry with the mouse or keyboard to
edit it; changing its channel link now preserves its identity. Links already
owned by another record are rejected. Use New application to clear the editor.
Copy uses the saved link, not an unsaved draft. Removal requires confirmation.
Search and background refresh preserve the current draft; changing server
clears the editor and filters. Save failures retain the previous stored state.
All actions in this tab are local; no bot permission or live Discord connection
is required. Acceptance does not assign roles or enable stream notifications.

## Creator role association (0.3.4)

Select a saved Creator; copy the Discord member ID and role ID using Developer
Mode. Save the association locally. Only a saved Accepted creator can request
Review and assign while connected to the same server. The preview shows actual
member/role names and IDs. Cancel sends no write. Confirm assigns only that role,
then reads membership back. Existing roles are retained; an already-present
role performs no write. Link changes, pausing or deleting local records do not
remove any Discord roles. No messages or stream notifications are sent.

Bot needs Manage Roles (or Administrator), membership in the server and its
highest role strictly above the selected role. Only existing non-managed roles
with zero guild-level permission bitfield are supported. Channel overwrites
may still grant that role access; they are not analyzed by this feature. No bulk
member enumeration is used. Mappings and delivery state remain local and are
excluded from the AI creator context. Unclear results are stored; there are no
automatic retries. A later user-triggered check reads membership before asking
for another assignment. A successful readback describes that moment, not a
permanent guarantee that a moderator will not later remove the role.

API references: https://docs.discord.com/developers/resources/guild#add-guild-member-role
and https://docs.discord.com/developers/topics/permissions#permission-hierarchy

0.3.5: if another operation starts while a confirmation dialog is open, the
role assignment is not started or recorded as sending. Wait for that operation
and review again. Poll publication likewise waits for an available worker.

## Delete a channel or category (0.3.6)

Connect Discord, then Discord → Manage channels → Delete channel/category.
Select the target (type/name/ID shown), enter an audit-log reason and choose
Review deletion. Inspect the server, target ID and effects, then type that exact
ID to enable Permanent delete. Cancel or a different ID sends no deletion.
The assistant can also prepare one delete request for an ID in the current
server context; execution goes through the same fresh preview/ID confirmation.
No AI request is required to use the form.

Deleting a category retains its child channels and removes their parent
association. The preview lists those children; changes to the target or child
list require a fresh preview. Deleting a channel is irreversible and removes
its contents; restoring an app backup cannot undo a Discord deletion. Bot
needs Manage Channels. Discord-protected Community rules/update channels are
rejected before deletion. Text, voice, category, announcement, stage, forum and
media supported; threads/DMs and recursive bulk deletion are not supported.
A successful response refreshes the overview. After an unclear error, inspect
Discord or refresh before trying again; no automatic retry. Local task,
community and credential records are preserved, including past activity data.

API reference: https://docs.discord.com/developers/resources/channel#deleteclose-channel
# Activity feedback in 0.3.7

Community → Activity System shows the capture date and the 24h **before that capture**, rather than implying that stored values describe the current 24 hours. After six hours, the capture is marked stale and participation suggestions use general ideas. Feedback refreshes once per minute while the app runs, including offline, without new Discord requests; edited drafts remain intact. Limited/unconfirmed coverage, future dates and unusable values are explicitly identified. For a new capture the bot needs View Channel and Read Message History in the selected channel. Counts cover accessible messages only, not the whole server or Voice activity.

## Activity permissions in 0.3.9

The Activity page shows its read-only requirements directly. In the selected Discord channel, open **Edit Channel → Permissions → bot role** and allow **View Channel** and **Read Message History** (German client: **Kanal ansehen** and **Nachrichtenverlauf anzeigen**). **Send Messages is not required.** If Discord rejects the channel lookup or message-history request, the page shows which access to check. Permission failures stop optional 15-minute retries and keep earlier samples; reconnect or capture again after correcting permissions. The app does not make a separate permission-probe request.

## Lobby Night drafts in 0.4.0

Community → Lobby Night validates 2–10 unique game suggestions (maximum 55 characters each) while you type. Save a local plan, select it to review its numbered choices, and correct title, time or suggestions before publication. Editing retains the plan identity and does not create another entry. Canceled plans and polls already scheduled, sending, unclear or published are locked to protect the reviewed delivery record. Suggestions are entered manually; the app does not read proposal-channel messages. Saving/editing creates no Discord event or message. Publishing a native poll still requires the separate preview and confirmation; scheduled publication still requires the app running and connected.
