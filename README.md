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
