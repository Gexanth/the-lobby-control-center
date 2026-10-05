# Development status — 0.2.2

Activity page now shows selected-channel metrics, a bounded history table and readable coverage limits. Each sample includes last-24-hour human message/participant counts within the latest 100 messages; hitting 100 flags potentially incomplete coverage. Snapshots overlap and must not be added together.

History is compatible with existing format-1 data. Retain at most 96 snapshots per channel and discard snapshots older than 30 days when recording; repeated samples in one 15-minute bucket replace that bucket's snapshot. No message content or author IDs are persisted. Failed history writes restore the previous in-memory server record and show an error instead of a success notification. Unchanged history tables do not rebuild.

Eleven unit tests cover history bounds, bucket replacement, retention, 24h boundaries, coverage limit, server isolation, rollback after write failure and the existing credentials/updater paths. Offscreen UI checks passed for history display, unchanged-table refresh and disconnect reset; table contrast inspected and corrected. Release status verified during publication. AI context includes the new coverage and 24h fields.

Next: consistent activity windows beyond the 100-message sample and reviewed Discord voting integration, following ROADMAP.md.
