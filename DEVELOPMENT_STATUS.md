# Development status — 0.2.1

UI and efficiency update: live overview cards, dashboard shortcuts, active sidebar state, Ctrl+1–8 navigation, scrollable pages for smaller windows, consistent button/tab styling, connection status and background-job indicator.

Fix: same-server overview refresh preserves the selected activity channel and optional polling. Server switch/disconnect resets polling. Community lists only rebuild when their data changes; selection is retained. Activity view shows channel names and local date/time instead of raw IDs/UTC strings.

Validated: eight unit tests; offscreen UI initialization, all navigation paths, dashboard values, busy state, 960×640 resize and disconnect reset. Signal-based check: 100 unchanged refreshes produced zero Creator list row insertions and preserved selection. No live Discord writes performed. Real Windows interaction remains to be confirmed by the user.

ROADMAP.md contains upcoming feature integrations. Dependencies and source updater protocol unchanged.
