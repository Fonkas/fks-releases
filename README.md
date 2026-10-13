# fks-releases

Posts every new GitHub Release of the FKS scripts on Discord — one place for all the repositories.

Every 15 minutes the workflow looks at the releases of every public `fks-*` repository of the owner and posts the
ones not announced yet (`announced.json`). A repository seen for the first time only has its current releases
recorded, so a new script never floods the channel. New `fks-*` repositories are picked up automatically.

## Setup

1. **Settings → Secrets and variables → Actions → New repository secret**
   - `DISCORD_RELEASE_WEBHOOK` = webhook URL of the changelog channel
   - or `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` to post with a bot (and auto-publish in an Announcement channel)
2. Optional **Variables**: `REPO_PREFIX` (default `fks-`), `DISCORD_NAME`, `DISCORD_AVATAR`, `DISCORD_COLOR`.
3. **Actions → Discord release announcements → Run workflow** once (records the current releases).

To announce a release again: **Run workflow** with the repository name (e.g. `fks-stables`).
