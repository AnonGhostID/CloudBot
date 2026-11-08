# CloudBot

CloudBot is a Python Telegram bot for mirroring and leeching files from the internet, torrents, and Telegram to Google Drive, rclone remotes, upload hosts, and Telegram. It uses Kurigram, a fork of Pyrogram. CloudBot is a fork of [mirror-leech-telegram-bot](https://github.com/anasty17/mirror-leech-telegram-bot), which is based on [python-aria-mirror-bot](https://github.com/lzzy12/python-aria-mirror-bot).

Current version: `v2.0.0-x0` (see `bot/version.py`). Licensed under GPLv3 (see [LICENSE](LICENSE)).

| ⬇️ Download | ⬆️ Upload | ⚙️ Manage |
| :-- | :-- | :-- |
| aria2c · qBittorrent · yt-dlp · Telegram | Google Drive · rclone · Telegram · 11 file hosts | MongoDB · RSS · Queues · File selection |

> **Start here:** [Quick start](#quick-start) · [Install](#installing) · [Docker](#running-with-docker) · [Commands](#bot-commands) · [Configuration](#configuration-reference)

<details>
<summary>🧭 <strong>Table of contents</strong></summary>

## Index

- [Features](#features)
- [Installing](#installing)
- [Running with Docker](#running-with-docker)
- [Quick start after the container is up](#quick-start)
- [Bot commands](#bot-commands)
- [Task arguments](#task-arguments)
- [Configuration reference](#configuration-reference)
- [Upload hosts](#upload-hosts)
- [Torrent file selector](#torrent-file-selector)
- [Direct links](#direct-links)
- [Service accounts](#service-accounts)
- [Generating `token.pickle`](#generating-tokenpickle)
- [Generating `rclone.conf`](#generating-rcloneconf)
- [Generating a MongoDB database](#generating-a-mongodb-database)
- [Updating from upstream](#updating-from-upstream)
- [Working files](#working-files)
- [Multi upload system](#multi-upload-system)
- [License and contributing](#license-and-contributing)

</details>

---

## Quick start

1. **Authorize yourself.** With the bot running, send `/login` in a private chat. The bot sends a temporary token to the owner's private chat. If `LOGIN_PASS` is set, use that password instead.
2. **Set the basics.** As owner or sudo, open `/bsetting` and set your upload destination. See `DEFAULT_UPLOAD` and [Upload hosts](#upload-hosts).
3. **Add Google credentials.** The bot runs without them, but Drive upload, clone, and search require them. Follow [Generating `token.pickle`](#generating-tokenpickle), then mount or upload the file and restart.
4. **Add rclone credentials.** The rclone modes need `rclone.conf`. Follow [Generating `rclone.conf`](#generating-rcloneconf).
5. **Run a first task.** Send a command with a link: `/mirror https://example.com/file` to mirror a file, or `/leech https://example.com/file` to upload it to Telegram. For torrents, use `/qbmirror <magnet>` or `/qbleech <magnet>`. Check progress with `/status`.

Video tutorials: [Wiszky's setup walkthrough](https://youtu.be/IUmq1paCiHI) ([GitHub](https://github.com/vishnoe115)) and the Tortoolkit repo's [Docker Compose and port-checking tutorial](https://youtu.be/c8_TU1sPK08).

---

## Features

<details>
<summary>✨ Supported features and integrations</summary>

- **aria2c downloads**: direct links, magnets, Telegram files, Google Drive files. File selection for torrents before and while downloading. Per-task and global seeding options, and `.netrc` authentication for protected links.
- **qBittorrent downloads**: the same, with global options edited from `/bsetting` while the bot runs. A non-negative global ratio or seeding-time limit enables it; `-1` disables it. A queued magnet with file selection waits for its queue slot and its metadata before showing the selector.
- **Telegram upload (leech)**: uploads to Telegram as document or media per user, with per-user split size, equal splits, media groups, thumbnails, and filename prefix, suffix, caption, and regex rename. Files over 2 GB upload with a premium account, over 4 GB with a user client. Leech output can go to a superGroup or channel. Downloading from Telegram uses a premium account when available, and restricted messages are reachable through private, public, or super links.
- **Upload hosts**: GoFile, StreamTape, PixelDrain, BuzzHeavier, AkiraBox, VikingFile, Filester, FileMirage, Transfer.it, storage.to, Filebin. Select all enabled hosts or one host per task with `-up gf|bh|pd|stp|ab|vf|fs|fm|tf|st|fb`, case-insensitive. A code selects that host even when its toggle is disabled. GitHub and release links also work. See [Upload hosts](#upload-hosts) for the details per host. Transfer, StreamTape login and other credentials live in [Upload host credentials](#upload-host-credentials).
- **Google Drive**: upload and clone with duplicate detection, download from Drive, count files and folders, and search files and folders across multiple roots, including Team Drives and recursive search. Uses `token.pickle` when a service-account key is absent, and a random service account per task.
- **Multiple status pages**: separate status views for download, upload, clone, queue, pause, seed, archive, extract, and split, with unlimited tasks paged. Upload, clone, archive, extract, and split can be cancelled, as can queue and pause tasks.
- **yt-dlp**: all supported sites, quality picker buttons, per-task and per-user default options, a whitelist of safe options, and embedded thumbnails.
- **Database (MongoDB)**: bot settings, user settings including thumbnails and rclone config, private files, RSS data, and incomplete tasks.
- **Torrent search**: through the Torrent Search API and through qBittorrent search plugins, including cached magnets from Real-Debrid.
- **Archives**: creation produces `.zip` only, with optional 7z split and an optional password. Extraction uses 7z and supports the 37 extensions listed in [Direct links](#direct-links). Split parts are joined and extracted with or without a password.
- **RSS feed**: per-user feeds with tags, filters, and pause, resume, and edit from the bot.
- **rclone**: upload and download with or without random service accounts, server-side clone, and per-user `rclone.conf`. Choose config, remote, and path from buttons, and set flags per task or globally.
- **Other**: Docker image support, asynchronous runtime with uvloop on the Kurigram fork of Pyrogram, editing variables and overwriting private files while the bot runs, updating at startup and with the restart command through `UPSTREAM_REPO`, Telegraph output, Mirror/Leech/Clone/Count/Del by reply, multiple links or files in a single command, custom names for non-torrent links, extension filter, a View Link button beside the index link, a queueing system for every task, zipping and unzipping multiple links into one directory, bulk download from a text file or a text message, joining files split with the Linux `split` package, and per-user bot limits.

Docker base image: `anonghostid/cloudbot-base:latest`, see the base image for your architecture.

</details>

## Installing

<details>
<summary>📦 Prerequisites and installation</summary>

Requirements: Python 3 with pip, and Docker.

Set `REPOSITORY_URL` to the repository you are deploying, then clone it:

```
git clone "$REPOSITORY_URL" cloudbot/ && cd cloudbot
```

On Debian-based distributions:

```
sudo apt install python3 python3-pip
```

Install Docker from the [official Docker documentation](https://docs.docker.com/engine/install/debian/).

On Arch and its derivatives:

```
sudo pacman -S docker python
```

Install the dependencies used by the setup scripts:

```
pip3 install -r requirements-cli.txt
```

</details>

## Running with Docker

<details>
<summary>🐳 Docker and Compose deployment</summary>

Build and run with Docker commands or Docker Compose. Compose is recommended.

### Config file

```
cp config_sample.env config.env
```

Remove the first line (`_____REMOVE_THIS_LINE_____=True`) and fill in the remaining fields. See the [configuration reference](#configuration-reference). The bot reads values through python-dotenv. Quotes are optional unless a value contains ` #` or spans multiple lines, as `SEARCH_PLUGINS` can. Without quotes, ` #` starts a comment. Changes made through `/bsetting` do not use this file.

### Build and run with official Docker commands

Start the Docker daemon if it is not already running:

```
sudo dockerd
```

Build the image:

```
sudo docker build . -t cloudbot
```

Run it with your configuration mounted at runtime:

```
sudo docker run --cap-drop=ALL --security-opt=no-new-privileges -v "$(pwd)/config.env:/usr/src/app/config.env" -v "$(pwd)/token.pickle:/usr/src/app/token.pickle" -p 80:80 -p 8080:8080 cloudbot
```

The `-p` flags publish the torrent file selector (`BASE_URL_PORT`, default `80`) and rclone serve endpoint (`RCLONE_SERVE_PORT`, default `8080`) on the host. Omit them if you do not need either endpoint. The committed `compose.yml` publishes no ports; add a `ports:` block to expose them.

Docker builds exclude local credentials and runtime data, including `token.pickle`, `accounts/`, `rclone.conf`, cookies, and Telegram session files. Mount whatever your deployment needs under `/usr/src/app`, or upload private files through bot settings. The example above mounts `token.pickle` for Google Drive OAuth.

The example and the Compose configuration drop Linux capabilities and prevent privilege escalation, but the image still runs as root, so isolate writable mounts and network access accordingly. Images built before these exclusions may contain private files. Inspect image layers before sharing them and rotate any credentials found in a published image.

Stop the container:

```
sudo docker ps
sudo docker stop id
```

### Build and run with Docker Compose

The committed `compose.yml` publishes no ports. Add a `ports:` block mapping `BASE_URL_PORT` (default `80`) and `RCLONE_SERVE_PORT` (default `8080`) if you want the torrent file selector and the rclone serve endpoint reachable from the host.

Install Docker Compose:

```
sudo apt install docker-compose
```

Build and run:

```
sudo docker-compose up
```

After editing files, for example with `nano start.sh`:

```
sudo docker-compose up --build
```

Stop, start, and view logs:

```
sudo docker-compose stop
sudo docker-compose start
sudo docker-compose up
```

### Docker notes

- Set `BASE_URL_PORT` and `RCLONE_SERVE_PORT` to the ports you want. Defaults are `80` and `8080`. Publishing to the host happens through `docker run -p` or a `ports:` block in `compose.yml`. The committed `compose.yml` publishes nothing.
- Stop the running container before deleting it, and delete the container before the image.
- Delete containers and images:

```
sudo docker container prune
sudo docker image prune -a
```

- Container pruning leaves images intact. Image pruning with `-a` removes all unused images.
- Check your machine's processing units with `nproc`, multiply by 4, and write the result to `AsyncIOThreadsCount` in `qBittorrent.conf`. Do not change `MaxRatioAction`.

</details>

## Bot commands

<details>
<summary>🤖 Bot command list</summary>

Set `SET_COMMANDS=True` to register bot commands with Telegram. See the [configuration reference](#configuration-reference).

```
start                               - Start / status. Private chat only. Takes no suffix.
mirror or /m                        - Mirror to Drive, rclone, or an upload host. Handles direct links, magnets, Drive links, and Telegram files.
qbmirror or /qm                     - Mirror a torrent with qBittorrent.
leech or /l                         - Upload to Telegram.
qbleech or /ql                      - Upload a torrent with qBittorrent.
ytdl or /y                          - Mirror a yt-dlp supported link.
ytdlleech or /yl                    - Upload a yt-dlp supported link.
clone or /c                         - Copy a file or folder on Drive, or on an rclone remote server-side.
count                               - Count files and folders on Drive.
del                                 - Delete a file or folder from Drive.
list                                - Search Drive for files or folders, with optional recursion and Telegraph output.
search                              - Search torrents through the Torrent Search API and qBittorrent plugins.
cancel[gid] / cancelbulk_gid        - Cancel one task, by reply or by GID.
cancelall / cancellallbot           - Cancel every task. Sudo only. No suffix on cancellallbot.
ctsel                               - Choose a Drive category or dump chat for an active task, by reply or GID, with -id or -index.
btsel[gid]                          - Choose torrent files, through Telegram buttons or the web selector at BASE_URL.
status or /s / statusall            - Paginated task status pages with throttled refresh. No suffix on statusall.
rss                                 - RSS subscriptions: sub, list, get, edit, pause, resume, unsubscribe. Sudo manages every feed and can start or stop the monitor.
usetting or /us                     - Your own settings, also in private chat, and directly with -s <key>.
bsetting or /bs                     - Bot settings for owner and sudo: variables, aria2c and qBittorrent options, private files, themes.
users                               - User statistics dump. Owner and sudo.
authorize or /a / unauthorize or /ua - Authorize or unauthorize a chat or user. Sudo only. Takes id, id:topic_id, or a reply.
addsudo / rmsudo                    - Add or remove sudo users.
blacklist or /bl / rmblacklist or /rbl - Block or unblock a user. Sudo only.
broadcast or /bc                    - Broadcast a reply to private-chat users. Sudo only and needs DATABASE_URL. Flags: -f/-forward, -q/-quiet, -d/-delete, -e/-edit.
gdclean or /gc                      - Empty one Drive folder. Owner only. Permanent or trash.
log                                 - Get the bot log. Sudo only.
restart or /r / restartall          - Restart the bot and apply updates. Sudo only. No suffix on restartall.
shell                               - Run shell commands. Owner only, also on edited messages.
eval / exec / clearlocals           - Run Python code and the exec helper. Owner only.
exportsession                       - Generate a Pyrogram user session string. Owner only, private chat. Flow: API_ID, API_HASH, PHONE, OTP, 2FA.
speedtest or /sp                    - Check server download and upload speed.
stats or /st                        - Bot usage statistics: CPU, RAM, disk, network, and versions.
ping or /p                          - Ping the bot.
help                                - Every command with its description, in basic, users, admin, and misc tiers.
login                               - Log in with LOGIN_PASS to skip the temporary-token system. Private chat only. Takes no suffix.
addimg / images                     - Add, list, and delete status-message images from graph.org links or a photo.
imdb                                - Search IMDB with a customizable template.
anime / animehelp / character / manga - AniList search for anime, characters, and manga, plus help.
mdl                                 - Search MyDramaList.
mediainfo or /mi                    - MediaInfo for a media file or URL, on Telegraph.
```

Every command except `start`, `login`, `cancellallbot`, `statusall`, `restartall`, `cancelbulk`, and `character`/`manga` takes the `CMD_SUFFIX` variable appended to its name. Set `SET_COMMANDS=True` to register the commands with Telegram automatically. `SET_COMMANDS` registers only a fixed subset of the commands, so a command missing from the Telegram menu can still work when typed.

With `SHOW_EXTRA_CMDS=True` these zip and unzip aliases also work: `/unzipmirror` `/uzm` `/zipmirror` `/zm`, `/qbunzipmirror` `/quzm` `/qbzipmirror` `/qzm`, `/ytdlzip` `/yz`, `/unzipleech` `/uzl` `/zipleech` `/zl`, `/qbunzipleech` `/quzl` `/qbzipleech` `/qzl`, and `/ytdlzipleech` `/yzl`.

</details>

## Task arguments

<details>
<summary>🧩 Command flags and arguments</summary>

Arguments work inline (`/cmd link -n new name`) or by replying to the link or file (`/cmd -n new name`). Every command accepts `-up`, `-rcf`, `-id`, `-index`, `-c`, `-ud`, `-ss`, and `-t` unless this section says otherwise.

| Argument | Meaning |
|---|---|
| `-n` / `-name` | Rename the file. Does not apply to torrents. |
| `-z` / `-zip [password]` | Zip after download. Zip commands imply this, and `-e` disables it. |
| `-e` / `-extract` / `-uz` / `-unzip [password]` | Extract an archive. With `-z` as well, extraction happens first. |
| `-up` / `-upload` | Destination: `gd`, `rc`, `rcl` for picking, `hosts`, one host code, `remote:path`, or `mrcc:remote:path` for your own `rclone/{uid}.conf`. See [Upload hosts](#upload-hosts). |
| `-b` / `-bulk [start[:end]]` | Bulk links from a text message or a `text/plain` file reply. Slice with `start:end`, default `0` to infinity. |
| `-i <n>` | Multi-link mode. Reply to the first link or file and give the count. |
| `-m` / `-sd` / `-samedir <folder>` | Multi-link and bulk tasks into one upload directory. Clears `-d` seed. |
| `-d` / `-seed [ratio[:minutes]]` | Seed the torrent, for example `-d 0.7:10`, `-d 0.7`, or `-d :10`. |
| `-s` / `-select` | Choose torrent files with qBittorrent, or yt-dlp quality. `-s` forces the picker even when a format is set. |
| `-u` / `-user`, `-p` / `-pass` | HTTP Basic authentication for direct links. |
| `-h` / `-headers k: v ...` | Extra headers for direct links. |
| `-j` / `-join` | Join split files. Runs before `-e` and `-z`. Usually used with `-m`. |
| `-rcf <flags>` | Extra rclone flags, in the form `--buffer-size:8M\|--drive-starred-only\|key\|key:value`. Overrides everything except `--exclude`. |
| `-id <id>` / `-index <url>` | Custom Drive folder id or link, plus its index URL. |
| `-c` / `-category <name>` | Drive category, from bot categories or UserTDs. `_` is a space. Case-insensitive. |
| `-ud` / `-dump <name\|@user\|-100…\|all>` | Dump chat. The bot must be an admin there. |
| `-ss` / `-screenshots <n>` | Screenshots per video file. Needs `SCREENSHOTS_MODE=True`. |
| `-t` / `-thumb <path\|link>` | Custom leech thumbnail, a Telegram link or a direct image URL. |
| `-opt` / `-options <k:v\|…>` | yt-dlp options for `/ytdl` mirror and leech. See `SAFE_YT_DLP_OPTIONS` in `yt_dlp_download.py`. Put `^` before numbers. |

`/clone` takes `link`, `-i`, `-up`, `-rcf`, `-id`, `-index`, and `-c`. `/ctsel` takes an optional GID plus `-id` and `-index`, and works for active `Downloading`, `Paused`, and `QueuedDl` tasks that are not leech tasks.

</details>

## Configuration reference

Copy `config_sample.env` to `config.env` and fill it in. The defaults below apply when a variable is empty. Differences in the sample configuration are noted.

<details>
<summary><strong>Required</strong> <sub>(4 options)</sub></summary>

### Required

| Variable | Meaning |
|---|---|
| `BOT_TOKEN` | The Telegram bot token from [@BotFather](https://t.me/BotFather). Changing it needs a restart. |
| `OWNER_ID` | The Telegram user ID of the bot owner, not the username. Changing it needs a restart. |
| `TELEGRAM_API` | Your Telegram API ID, from https://my.telegram.org, for downloading Telegram files. Changing it needs a restart. |
| `TELEGRAM_HASH` | Your Telegram API hash, from https://my.telegram.org, for downloading Telegram files. Changing it needs a restart. |

</details>

<details>
<summary><strong>Optional core</strong> <sub>(17 options)</sub></summary>

### Optional core

| Variable | Meaning |
|---|---|
| `USER_SESSION_STRING` | A session string for your Telegram account, used to download and upload from your account and to send RSS. Required for Telegram links, restricted files, and for 4 GiB splits with a premium user client. Generate one with `/exportsession` in a private chat, as owner. It asks for API_ID, API_HASH, PHONE, OTP, and 2FA. The user client cannot run in a private chat, so authorize the group and use the bot in a superGroup. Changing it needs a restart. |
| `DATABASE_URL` | Your MongoDB connection string. See [Generating a MongoDB database](#generating-a-mongodb-database). Data saved here includes auth and sudo users, user settings including thumbnails, RSS data, and incomplete tasks. Changing it needs a restart. |
| `DOWNLOAD_DIR` | Local folder for downloads. Default `/usr/src/app/downloads/`. Changing it needs a restart. |
| `CMD_SUFFIX` | Appended to every command name. Changing it needs a restart. |
| `AUTHORIZED_CHATS` | User and group ids to authorize, separated by space. Format `chat_id[:topic_id ...]`. Changing it needs a restart. |
| `SUDO_USERS` | User ids with sudo permission, separated by space. Changing it needs a restart. |
| `BLACKLIST_USERS` | User ids blocked from using the bot, separated by space. Changing it needs a restart. |
| `STATUS_LIMIT` | Tasks shown per status page. Code default `6`. The sample ships `4`. Forced to `2` when `IMAGES` is set. Fewer tasks per page holds up better under load. |
| `DEFAULT_UPLOAD` | `rc` uploads to `RCLONE_PATH`, `gd` to `GDRIVE_ID`, `hosts` to the enabled upload hosts, or a single host code. Default `gd`. |
| `STATUS_UPDATE_INTERVAL` | Seconds between status message updates. `10` or more is recommended. |
| `AUTO_DELETE_MESSAGE_DURATION` | Seconds after which the bot deletes its own message and the command message. Code default `30`. The sample ships `60`. |
| `INCOMPLETE_TASK_NOTIFIER` | Send incomplete task messages after a restart. Needs `DATABASE_URL` and a superGroup. Default `False`. |
| `SET_COMMANDS` | Register bot commands with Telegram automatically, so you do not need BotFather. Default `False`. |
| `EXTENSION_FILTER` | File extensions that will not upload or clone, separated by space. No leading dot needed. |
| `YT_DLP_OPTIONS` | Default yt-dlp options, as `key:value\|key:value`. Put `^` before numeric values. Lists, tuples, and dictionaries must be Python literals, not expressions. Only options in `SAFE_YT_DLP_OPTIONS` are accepted. Executable commands, custom postprocessors, executable locations, and filesystem path options are rejected for security. The same rules apply to user settings and to `-opt`. Example: `format:bv*+mergeall[vcodec=none]\|nocheckcertificate:True`. |
| `FSUB_IDS` | Chat ids of groups or channels whose members must subscribe, separated by space. Format `-100xxxxxx`. The bot must be an admin in each of them. |
| `BOT_PM` | Send files and links to the bot's private chat. Default `False`. |

</details>

<details>
<summary><strong>Google Drive</strong> <sub>(9 options)</sub></summary>

### Google Drive

| Variable | Meaning |
|---|---|
| `GDRIVE_ID` | Folder or Team Drive id, or `root`, for uploads made with google-api-python-client. |
| `USER_TD_MODE` | Let users upload into their own Drive. Default `False`. |
| `USER_TD_SA` | Show your service account in user settings so users add it to their own Team Drive. Use an email or group email such as `service-accounts\@example.com`. |
| `INDEX_URL` | Index for Drive links, see https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index. |
| `USE_SERVICE_ACCOUNTS` | Use service accounts with google-api-python-client. See [Service accounts](#service-accounts). Default `False`. |
| `IS_TEAM_DRIVE` | Uploading to a Team Drive with google-api-python-client. Default `False`. |
| `STOP_DUPLICATE` | Stop a task when a file or folder with the same name already exists in `GDRIVE_ID`. Compares names, not hashes. Default `False`. |
| `DISABLE_DRIVE_LINK` | Hide the Drive link button. Default `False`. |
| `GD_INFO` | Description written on uploaded Drive files. Default `Uploaded by CloudBot`. |

</details>

<details>
<summary><strong>APIs and cookies</strong> <sub>(5 options)</sub></summary>

### APIs and cookies

| Variable | Meaning |
|---|---|
| `REAL_DEBRID_API` | API key for Real-Debrid. Supports premium download-limit bypass and cached magnets. |
| `DEBRID_LINK_API` | API key for Debrid-Link. Supports premium download-limit bypass. |
| `FILELION_API` | API key for FileLions download pages. Their `/live`, `/to`, and `/online` links all work with it. |
| `GDTOT_CRYPT` | Used to bypass Gdtot links. |
| `JIODRIVE_TOKEN` | Token used to bypass JioDrive links. |

</details>

<details>
<summary><strong>rclone</strong> <sub>(6 options)</sub></summary>

### rclone

| Variable | Meaning |
|---|---|
| `RCLONE_PATH` | Default rclone path for uploads with rclone. |
| `RCLONE_FLAGS` | Flags as `key:value\|key\|key\|key:value`. See all [rclone flags](https://rclone.org/flags/). |
| `RCLONE_SERVE_URL` | Public URL of the bot, for rclone serve. Format `http://myip`, or `http://myip:port` when the port is not `80`. HTTP, not HTTPS. |
| `RCLONE_SERVE_PORT` | Port for `RCLONE_SERVE_URL`. Default `8080`. |
| `RCLONE_SERVE_USER` | Username for rclone serve authentication. |
| `RCLONE_SERVE_PASS` | Password for rclone serve authentication. |

</details>

<details>
<summary><strong>Updates</strong> <sub>(3 options)</sub></summary>

### Updates

| Variable | Meaning |
|---|---|
| `UPSTREAM_REPO` | Repository the bot updates from on each restart. For a private repository use `https://username:{githubtoken}@github.com/{username}/{reponame}`, with the token from [GitHub settings](https://github.com/settings/tokens). See [Updating from upstream](#updating-from-upstream). |
| `UPSTREAM_BRANCH` | Branch to update from. Default `master`. |
| `UPGRADE_PACKAGES` | When `True`, `update.py` reinstalls every installed package with `uv pip install` before starting the bot. Default `False`. |

</details>

<details>
<summary><strong>Telegram leech and mirror</strong> <sub>(12 options)</sub></summary>

### Telegram leech and mirror

| Variable | Meaning |
|---|---|
| `LEECH_SPLIT_SIZE` | Split size in bytes. Default `2 GB`, or `4 GB` with a premium account. |
| `AS_DOCUMENT` | Upload Telegram files as documents instead of as media. Default `False`. |
| `EQUAL_SPLITS` | Split files above `LEECH_SPLIT_SIZE` into equal parts. Does not work with the zip command. Default `False`. |
| `MEDIA_GROUP` | Show split parts as a media group. Default `False`. |
| `CAP_FONT` | HTML tag wrapping the leech filename caption: `b`, `i`, `u`, `s`, `spoiler`, `code`. Default `code` in the sample. |
| `LEECH_FILENAME_PREFIX` | Prefix added to leeched filenames. |
| `LEECH_FILENAME_SUFFIX` | Suffix added to leeched filenames. |
| `LEECH_FILENAME_CAPTION` | Caption added to leeched files. |
| `LEECH_FILENAME_REMNAME` | Word removed from leeched filenames. |
| `MIRROR_FILENAME_PREFIX` | Prefix added to mirrored filenames. |
| `MIRROR_FILENAME_SUFFIX` | Suffix added to mirrored filenames. |
| `MIRROR_FILENAME_REMNAME` | Word removed from mirrored filenames. |

</details>

<details>
<summary><strong>Log channels and superGroups</strong> <sub>(3 options)</sub></summary>

### Log channels and superGroups

| Variable | Meaning |
|---|---|
| `LEECH_LOG_ID` | Chat id for leech uploads. SuperGroup or channel only. Add `-100` before a channel or superGroup id. Do not add the bot id or your own id. For topics use `chat_id:topic_id`. Multiple ids are allowed, separated by space, but multiple topics are not supported yet. |
| `MIRROR_LOG_ID` | Chat id for mirror uploads. Same rules as `LEECH_LOG_ID`. |
| `LINKS_LOG_ID` | Chat id for link logs. Same rules as `LEECH_LOG_ID`. |

</details>

<details>
<summary><strong>qBittorrent and aria2c</strong> <sub>(4 options)</sub></summary>

### qBittorrent and aria2c

| Variable | Meaning |
|---|---|
| `TORRENT_TIMEOUT` | Timeout in seconds for dead torrents, for both qBittorrent and aria2c. |
| `BASE_URL` | Public URL of the bot, for the torrent web file selector, in the form `http://myip` or `http://myip:port`. HTTP, not HTTPS. |
| `BASE_URL_PORT` | Port for `BASE_URL`. Default `80`. |
| `WEB_PINCODE` | Show the PIN as a separate `btsel pin` button in Telegram instead of embedding it in the `Select Files` URL. Default `False`. The web selector always needs the 4-digit PIN. See [Torrent file selector](#torrent-file-selector). |

Note for qBittorrent on low memory: limit `MaxConnections`, lower `AsyncIOThreadsCount`, set `DiskWriteCacheSize` to `32`, and lower `MemoryWorkingSetLimit` in `qbittorrent.conf` or through the `/bsetting` command.

</details>

<details>
<summary><strong>Queue system</strong> <sub>(3 options)</sub></summary>

### Queue system

| Variable | Meaning |
|---|---|
| `QUEUE_ALL` | Maximum combined active downloads and uploads. `QUEUE_DOWNLOAD` and `QUEUE_UPLOAD` are independent limits and also apply when set. An unset or zero limit is unlimited. |
| `QUEUE_DOWNLOAD` | Number of parallel downloading tasks. |
| `QUEUE_UPLOAD` | Number of parallel uploading tasks. |

A direct multi-file download fails when any file cannot be downloaded. The error names the failed files instead of uploading an incomplete result. Direct-link resolver requests use a 30 second timeout. Real-Debrid magnet polling stops after five minutes, on a terminal provider error, or when the task is cancelled.

</details>

<details>
<summary><strong>RSS</strong> <sub>(2 options)</sub></summary>

### RSS

| Variable | Meaning |
|---|---|
| `RSS_DELAY` | Refresh interval in seconds. Default `600`. |
| `RSS_CHAT` | Chat id where RSS links are sent. Add `-100` before a channel id. `RSS_CHAT` is required or the monitor will not work. You need `USER_SESSION_STRING` or a channel. With a channel, add the bot to both the channel and the group linked to it, and set `RSS_CHAT` to the channel id so messages sent to the channel are forwarded to the group. With `USER_SESSION_STRING`, set `RSS_CHAT` to the group id. Without `DATABASE_URL` you will miss feeds while the bot is offline. |

</details>

<details>
<summary><strong>Limits</strong></summary>

### Limits

`DAILY_TASK_LIMIT`, `DAILY_MIRROR_LIMIT`, `DAILY_LEECH_LIMIT`, `USER_MAX_TASKS`, `BOT_MAX_TASKS`, `TORRENT_LIMIT`, `DIRECT_LIMIT`, `GDRIVE_LIMIT`, `CLONE_LIMIT`, `YTDLP_LIMIT`, `PLAYLIST_LIMIT`, `LEECH_LIMIT`, `STORAGE_THRESHOLD`, and `USER_TIME_INTERVAL`.

Size limits in GB: `TORRENT_LIMIT`, `DIRECT_LIMIT`, `GDRIVE_LIMIT`, `CLONE_LIMIT`, `YTDLP_LIMIT`, `LEECH_LIMIT`, `STORAGE_THRESHOLD`, `DAILY_MIRROR_LIMIT`, and `DAILY_LEECH_LIMIT`. Task and item counts: `DAILY_TASK_LIMIT`, `USER_MAX_TASKS`, `BOT_MAX_TASKS`, and `PLAYLIST_LIMIT`. `USER_TIME_INTERVAL` sets the gap in seconds between consecutive mirror or leech operations by one user, default `0`. `STORAGE_THRESHOLD` reserves free disk space; the bot cancels downloads that would leave less than this amount.

</details>

<details>
<summary><strong>Templates</strong> <sub>(3 options)</sub></summary>

### Templates

| Variable | Meaning |
|---|---|
| `ANIME_TEMPLATE` | Template for anime search results. |
| `IMDB_TEMPLATE` | Template for IMDB search results. |
| `MDL_TEMPLATE` | Template for MyDramaList search results. |

</details>

<details>
<summary><strong>Telegraph</strong> <sub>(4 options)</sub></summary>

### Telegraph

| Variable | Meaning |
|---|---|
| `TITLE_NAME` | Title for Telegraph pages from `/list`. Default `CloudBot`. |
| `AUTHOR_NAME` | Author name for Telegraph pages. Default `CloudBot`. |
| `AUTHOR_URL` | Author URL for Telegraph pages. |
| `COVER_IMAGE` | Header image for Telegraph pages. Use a graph.org link. |

</details>

<details>
<summary><strong>Extra</strong> <sub>(10 options)</sub></summary>

### Extra

| Variable | Meaning |
|---|---|
| `SAFE_MODE` | Hide filenames and links from authorized groups: remove filenames, remove the leech index link, and remove the mirror link. The links go to private chat instead, so set `BOT_PM=True`. |
| `DELETE_LINKS` | Delete links after use. Default `False`. |
| `CLEAN_LOG_MSG` | Remove the leech-started message from the leech log. Default `False`. |
| `SHOW_EXTRA_CMDS` | Enable the old zip and unzip command aliases listed in [Bot commands](#bot-commands). Default `False`. |
| `TIMEZONE` | Timezone for the bot, from [this list](https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568). Code fallback `Asia/Kolkata`. The sample ships `Asia/Jakarta`. |
| `IMAGES` | Status-message images as graph.org links separated by space. Setting them forces `STATUS_LIMIT` to `2`. |
| `IMG_SEARCH` | Keywords for downloading images from WallpaperFlare at startup, separated by comma, for example `anime`, `iron man`, `god of war`. Finding images sets `STATUS_LIMIT` to `2` as well. |
| `IMG_PAGE` | Page number for image downloads. Each page returns about 70 images. |
| `BOT_THEME` | Theme of the bot. Built in: `minimal` (default and fallback), `classic`, `neon`, `random`. The sample ships `neon`. Telegram buttons use blue for navigation and links, green for confirmations and enabled states, and red for destructive actions. Colors depend on the Telegram client. To add your own theme, copy `cloudbot_minimal.py` in `bot/helper/themes/` to `cloudbot_<name>.py`, keep `class CloudBotStyle` and the `{...}` placeholder names, and set `BOT_THEME=<name>`. No registration is needed. |
| `EXCEP_CHATS` | SuperGroup ids where logging is disabled for that group only. Other authorized chats keep logging. Add `-100` before a superGroup id. Do not add the bot id or your own id. |

</details>

<details>
<summary><strong>File buttons</strong> <sub>(4 options)</sub></summary>

### File buttons

| Variable | Meaning |
|---|---|
| `SHOW_MEDIAINFO` | MediaInfo button on files. Default `False`. |
| `SCREENSHOTS_MODE` | Generate screenshots with the `-ss` argument. Default `False`. |
| `SAVE_MSG` | Save button on files and links so users can save them directly without forwarding. Default `False`. |
| `SOURCE_LINK` | Source button on files and links. Default `False`. |

</details>

<details>
<summary><strong>Token system</strong> <sub>(2 options)</sub></summary>

### Token system

| Variable | Meaning |
|---|---|
| `TOKEN_TIMEOUT` | Temporary token timeout per group member in seconds. Empty disables the temporary-token system. |
| `LOGIN_PASS` | Permanent password that skips the token system. |

</details>

<details>
<summary><strong>Torrent search</strong> <sub>(3 options)</sub></summary>

### Torrent search

| Variable | Meaning |
|---|---|
| `SEARCH_API_LINK` | URL of the search API. Get your API from [this repository](https://github.com/Ryuk-me/Torrent-Api-py). Supported sites are discovered live from `GET {SEARCH_API_LINK}/api/v1/sites`, under `/api/v1/{all,site}/...`. |
| `SEARCH_LIMIT` | Result limit per site for the search API, not an overall limit. Default `0`, which means the API's own default per site. |
| `SEARCH_PLUGINS` | List of qBittorrent search plugins as raw GitHub links. Plugins already included can be removed. The main source is [qBittorrent Search Plugins, official and unofficial](https://github.com/qbittorrent/search-plugins/wiki/Unofficial-search-plugins). |

</details>

## Upload hosts

<details>
<summary>☁️ Upload services, limits, and credentials</summary>

The supported upload destinations are Google Drive, rclone remotes, and these upload hosts:

| Code | Host | Folders | Credentials | Notes |
|---|---|---|---|---|
| `gf` | GoFile | Yes | Required API key | |
| `bh` | BuzzHeavier | No | Required key | |
| `pd` | PixelDrain | No | Required key | |
| `stp` | StreamTape | Yes | Required, as `login:key` | Videos only; folders are filtered to videos, and a Telegraph page is returned. |
| `ab` | AkiraBox | No | Anonymous | One file up to 5 GiB. Guest links expire after 7 days without a download. |
| `vf` | VikingFile | No | Anonymous | |
| `fs` | Filester | No | Anonymous | |
| `fm` | FileMirage | No | Anonymous | Uploads in 99 MiB chunks. May change, as it uses the site's upload flow. |
| `tf` | Transfer.it | No | Anonymous | Uses the `transferit-py` client. |
| `st` | storage.to | No | Anonymous | Free tier supports files up to 25 GB and expires uploads. Anonymous uploads have daily file and bandwidth quotas. |
| `fb` | Filebin | No | Anonymous | |

Use `-up` with a code, case-insensitive, to choose one host for one task. It works even when that host's toggle is disabled. GitHub release links are also supported.

GoFile and StreamTape accept folders. StreamTape accepts video files only: `.avi`, `.mkv`, `.mpg`, `.mpeg`, `.vob`, `.wmv`, `.flv`, `.mp4`, `.mov`, `.m4v`, `.m2v`, `.divx`, `.3gp`, `.webm`, `.ogv`, `.ogg`, `.ts`, `.ogm`. Every other host accepts one file.

AkiraBox uses its undocumented guest upload flow, which can change. Transfer.it uses the community maintained `transferit-py` client. storage.to has an optional `STORAGETO_API_KEY` that attaches uploads to an account. Filebin and storage.to share links resolve for downloads. storage.to resolution uses the site's download flow and fails when Cloudflare or Turnstile challenges it. Signed download URLs may expire while a task is queued.

</details>

### Upload host credentials

<details>
<summary>🔑 Shared and per-user credentials</summary>

`GOFILE_API_KEY`, `PIXELDRAIN_API_KEY`, `BUZZHEAVIER_API_KEY`, `STREAMTAPE_CREDENTIALS` (in the form `login:key`), `VIKINGFILE_API_KEY` (a user hash), `FILESTER_API_KEY`, `FILEMIRAGE_API_KEY`, and `STORAGETO_API_KEY` in `config.env` are shared fallbacks for every authorized bot user. Credentials saved by a user take precedence. A shared credential does not enable a host on its own. Enable each host in User Settings for multi-host uploads.

</details>

## Torrent file selector

<details>
<summary>🧲 Torrent selection, web PIN, and seeding</summary>

The bot starts a file selector through Flask served by gunicorn when `BASE_URL` is set, as `gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent`. Default `BASE_URL_PORT` is `80`. The standalone `app.run()` in `web/wserver.py` is only for local debugging.

Routes:

- `GET /` shows a static landing page.
- `GET /app/files/<id_>` shows the file tree selector. The id is an aria2 GID, or a qBittorrent hash when its length is above 20. Without a `pin_code` parameter this route returns the PIN entry page, not the tree.
- `POST /app/files/<id_>` applies `filenode_*` priorities, through `torrents_file_priority` or `change_option select-file`, and retries while it does so.

The PIN is 4 digits, taken as the first 4 digit characters of `<id_>`, which is not the same as its first 4 characters when a GID has letters. A wrong PIN returns `Incorrect pin code`. `WEB_PINCODE` only changes the Telegram button, a direct `Select Files` URL or a separate `btsel pin` button. The web side always asks for the PIN. There is no proxy or index route here. Downloading and index serving are done by rclone serve or a Drive index, not by `web/`.

`btsel` with an optional GID pauses the task in Telegram and shows `Select Files`, `Pincode`, `Done Selecting`, and `Cancel`. Aria2 paths must live under `{DOWNLOAD_DIR}<digits>/...`.

### Seeding

Using `-d` alone uses the global options for aria2c or qBittorrent.

For qBittorrent the globals are `GlobalMaxRatio` and `GlobalMaxSeedingMinutes` in `qBittorrent.conf`. `-1` means no limit, and the torrent can still be cancelled manually. Do not change `MaxRatioAction`.

For aria2c the global is `--seed-ratio=0`, no limit, in `aria.sh`. There is no global `--seed-time`. Per-task `-d ratio:minutes` is applied per download. `aria.sh` also runs aria2c as a daemon with RPC on `localhost:6800`, and `bot/__init__.py` runs `qbittorrent-nox -d --profile=$(pwd)`, with WebUI on `localhost:8090`.

</details>

## Direct links

<details>
<summary>🔗 Direct-link hosts and resolver notes</summary>

Supported directly by the resolver:

mediafire (folder), letsupload.io, streamtape.com and its mirrors, upload.ee, pixeldrain.com, pixeldra.in, buzzheavier.com, hxfile.co, filepress, racaty.net, 1fichier.com, 1drv.ms (file only, not folders or business accounts), uptobox.com (through the debrid APIs only) and solidfiles.com, streamvid.net, linkbox.to (linkbox.cloud, lbx.to, teltobx.net, telbx.net), shrdsk.me, wetransfer.com and we.tl, gofile.io (folder), filelions.com/live/to/online (`FILELION_API` required), transfer.it, filebin.net, storage.to, fuckingfast.co, krakenfiles.com, qiwi.gg, github.com, easyupload.io, dood.* (18 domains), terabox share links (15 domains), gdtot, filepress, filebee, appdrive, gdflix, and jiodrive share links, GDrive index links (`.../N:/`), and Real-Debrid and Debrid-Link hosters (see `debrid_sites` and `debrid_link_sites` in `direct_link_generator.py`).

`mdisk.me` and other yt-dlp-only hosts work through `/ytdl` or `/ytdlleech`, not through the direct-link resolver. AnonFiles-based sites are rejected.

HXFile needs Netscape-format cookies in `hxfile.txt` in the bot's working directory. Upload them through the bot's private-file settings, or mount them into the container.

BuzzHeavier file and folder links use a Chrome-like HTTP fingerprint and the site's `Hx-Redirect` download URLs. Folder entries can lack a download URL when the site does not return one.

PixelDrain file links are converted to `https://cdn.pixeldrain.eu.cc/<file-id>` for downloads.

MediaFire links need Cloudflare verification that the bot cannot complete. Open the page in a browser and send the direct download URL to the bot. Direct URLs may expire.

Transfer.it links, in the form `https://transfer.it/t/...`, support files and folders. For password-protected transfers, append `::password` to the URL or pass the password with `-p`. The same `::password` suffix works for MediaFire, GoFile, 1fichier, and EasyUpload.

Archives use 7z for extraction and support these 37 extensions: `.tar.bz2`, `.tar.gz`, `.bz2`, `.gz`, `.tar.xz`, `.tar`, `.tbz2`, `.tgz`, `.lzma2`, `.zip`, `.7z`, `.z`, `.rar`, `.iso`, `.wim`, `.cab`, `.apm`, `.arj`, `.chm`, `.cpio`, `.cramfs`, `.deb`, `.dmg`, `.fat`, `.hfs`, `.lzh`, `.lzma`, `.mbr`, `.msi`, `.mslz`, `.nsis`, `.ntfs`, `.rpm`, `.squashfs`, `.udf`, `.vhd`, `.xar`.

</details>

## Service accounts

<details>
<summary>🔐 Set up Google service accounts</summary>

Service accounts require `USE_SERVICE_ACCOUNTS=True` in the config file or environment. They are recommended only for Team Drive uploads.

*> Abuse of this feature is not the aim of this project. Do not make many projects. One project with 100 service accounts allows plenty of use, and over-abusing it can get your projects banned by Google.*

*> One service account can upload or copy around 750 GB a day. One project can hold 100 service accounts, so one project can upload 75 TB a day. Everyone can copy *`2TB/DAY`* from each file creator (uploader account), so a *`userRateLimitExceeded`* error means the file creator's limit is exceeded, which is *`2TB/DAY`*, not yours.*

### 1. Generate service accounts

[What is a service account?](https://cloud.google.com/iam/docs/service-accounts)

Create only the service accounts you need. To download keys again for accounts created with this script, run:

```
python3 gen_sa_accounts.py --download-keys $PROJECTID
```

#### Two methods

##### 1. Create service accounts in an existing project (recommended)

List your project ids:

```
python3 gen_sa_accounts.py --list-projects
```

Enable services automatically:

```
python3 gen_sa_accounts.py --enable-services $PROJECTID
```

Create service accounts in the current project:

```
python3 gen_sa_accounts.py --create-sas $PROJECTID
```

Download the service-account keys to the accounts folder:

```
python3 gen_sa_accounts.py --download-keys $PROJECTID
```

##### 2. Create service accounts in a new project

```
python3 gen_sa_accounts.py --quick-setup 1 --new-only
```

A folder named `accounts` is created, containing keys for the service accounts.

### 2. Add service accounts

#### Two methods

##### 1. Add them to a Google Group, then to a Team Drive (recommended)

Enter the accounts folder:

```
cd accounts
```

Extract the account emails into `emails.txt` in this folder.

For Windows using PowerShell:

```
$emails = Get-ChildItem .\\**.json |Get-Content -Raw |ConvertFrom-Json |Select -ExpandProperty client_email >>emails.txt
```

For Linux:

```
grep -oPh '"client_email": "\K[^"]+' *.json > emails.txt
```

Return to the repository folder:

```
cd ..
```

Add the emails from `emails.txt` to a Google Group, then add that Google Group to your Shared Drive, promote it to manager, and delete `emails.txt` from the accounts folder.

##### 2. Add them to a Team Drive directly

Run:

```
python3 add_to_team_drive.py -d SharedTeamDriveSrcID
```

</details>

## Generating `token.pickle`

<details>
<summary>📖 Generate a Google Drive token</summary>

Generate `token.pickle` on a local machine with a browser, such as a Termux setup. The older authentication flow does not work from the bot or Replit. Open the link from `generate_drive_token.py` in a local browser. Windows users need Python 3 and pip; see [Wiszky's tutorial](https://telegra.ph/Create-Telegram-Mirror-Leech-Bot-by-Deploying-App-with-Heroku-Branch-using-Github-Workflow-12-06) ([GitHub](https://github.com/vishnoe115)).

1. Visit the [Google Cloud Console](https://console.developers.google.com/apis/credentials).
2. Open the OAuth Consent tab, fill it in, and save.
3. Open the Credentials tab and click Create Credentials, then OAuth Client ID.
4. Choose Desktop and create.
5. Publish your OAuth consent screen app to prevent `token.pickle` from expiring.
6. Use the download button to download your credentials.
7. Move that file to the root of the bot, and rename it to `credentials.json`.
8. Visit the [Google API page](https://console.developers.google.com/apis/library).
9. Search for the Google Drive API and enable it.
10. Run the script to generate `token.pickle`:

```
pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib
python3 generate_drive_token.py
```

</details>

## Generating `rclone.conf`

<details>
<summary>📖 Generate an rclone configuration</summary>

1. Install rclone from the [official site](https://rclone.org/install/).
2. Run `rclone config` to create one or more remotes.
3. Follow the steps to generate `rclone.conf`.
4. Copy `rclone.conf` from `.config/rclone/rclone.conf` to the repo folder.

A sample `rclone.conf` looks like:

```
[Name]
- root_id :
```

</details>

## Generating a MongoDB database

<details>
<summary>🍃 Optional MongoDB setup</summary>

MongoDB is optional. Leave `DATABASE_URL` empty to run without it. When it is configured, the bot uses the `cloudbot` database, and the MongoDB user must have access to that database.

1. Go to https://mongodb.com/ and sign up.
2. Create a shared cluster.
3. Under the Deployment header, press on Database. Your cluster is there.
4. Press on connect. Choose Allow Access From Anywhere, add the IP address without editing it, then create a user.
5. After creating the user, press on Choose a connection and then Connect your application. Choose the Python driver and version 3.6 or later.
6. Copy the connection string, replace `<password>` with your user's password, then close.

</details>

## Updating from upstream

<details>
<summary>🔄 Upstream updates and precautions</summary>

`UPSTREAM_REPO` can edit and add any file in the repository.

- Set a public or private repository URL to fetch its files and overwrite local copies.
- A private upstream repository can supply private files such as `token.pickle` or the accounts folder after deployment.
- Upstream copies replace private files included at deployment. Private files saved in the database take precedence over both.
- When upstream changes `requirements.txt`, the bot may fail to start after a restart. Redeploy with the updated dependencies, or point `UPSTREAM_REPO` to a fork that retains the previous requirements.
- Check dependency changes when merging official commits into your fork, too.
- Upstream changes take effect after a restart.

</details>

## Working files

<details>
<summary>🗃️ Working-file examples</summary>

Optional files read from the bot's working directory.

### Multi Drive search list

To search multiple Team Drives or folders, run `driveid.py` and follow its prompts to generate `list_drives.txt`. You can also create the file in the working directory with this format:

```
DriveName folderID/tdID or `root` IndexLink(if available)
DriveName folderID/tdID or `root` IndexLink(if available)
```

Example:

```
TD1 root https://example.dev
TD2 0AO1JDB1t3i5jUk9PVA https://example.dev
```

### Multi shortener

To use multiple shorteners for link generation, create a `shorteners.txt` file in the working directory in this format:

```
shortener_domain shortener_api_key
```

Example:

```
urlshortx.com 91fc872f9882144c27eecdc22d16f7369766f297
ouo.io LYT0zBn1
```

Supported URL shorteners: exe.io, gplinks.in, shrinkme.io, urlshortx.com, shortzon.com, bit.ly, shorte.st, linkvertise.com, ouo.io, cutt.ly.

### Extra start buttons

Drive Link, Index Link, and View Link are built-in buttons. To add up to four extra buttons, create `buttons.txt` in the working directory with this format:

```
button_name button_url
```

Example:

```
Documentation https://docs.python.org/3/
Telegram_API https://core.telegram.org/bots/api
```

To put a space in a button name, use `_`.

### yt-dlp and aria2c authentication with `.netrc`

For premium accounts in yt-dlp, or for protected index links, create a `.netrc` file in this format:

```
machine host login username password my_password
```

Example:

```
machine instagram login doc.adhikari password mypassword
```

Name the file `.netrc`, not `netrc`. Enable hidden files in your file manager to find it.

For Instagram, you must log in even to download public posts, and after the first try you must confirm, from your phone app, that you logged in from a different IP.

For YouTube authentication use a [cookies.txt](https://github.com/ytdl-org/youtube-dl#how-do-i-pass-cookies-to-youtube-dl) file.

For aria2c, use the bot's built-in authentication with or without a username. For example, an index link without a username:

```
machine example.workers.dev password index_password
```

For yt-dlp, use the extractor name as the host, such as instagram or Twitch. Add each account on a separate line.

</details>

## Multi upload system

<details>
<summary>🚀 Upload destinations and settings</summary>

`RCLONE_PATH` sets the default rclone destination; `GDRIVE_ID` sets the default Drive destination. `DEFAULT_UPLOAD` chooses which destination to use.

- When `DEFAULT_UPLOAD` is `rc`, fill `RCLONE_PATH` with a path as the default, or with `rcl` to select a destination path on each new task.
- When `DEFAULT_UPLOAD` is `gd`, fill `GDRIVE_ID` with a folder or Team Drive id.
- When `DEFAULT_UPLOAD` is `hosts`, uploads use the enabled upload hosts configured in user settings. A host code selects that host only.
- Existing `DEFAULT_UPLOAD=ddl` settings are migrated to `hosts`. When the value comes from an external environment, change it there to `hosts`.
- Mount `rclone.conf` at `/usr/src/app/rclone.conf` when running the Docker container, or use bot settings to upload it as a private file.
- When `rclone.conf` is uploaded from user settings or added at `rclone/{user_id}.conf`, `RCLONE_PATH` must start with `mrcc:`.
- When entering a path manually for a user configuration, prefix it with `mrcc:`.
- Use `-up gf` for GoFile, `-up bh` for BuzzHeavier, `-up pd` for PixelDrain, `-up stp` for StreamTape, `-up ab` for AkiraBox, `-up vf` for VikingFile, `-up fs` for Filester, `-up fm` for FileMirage, `-up tf` for Transfer.it, `-up st` for storage.to, or `-up fb` for Filebin. Codes are case-insensitive and select only that host, even when its toggle is disabled. StreamTape requires `login:key`.
- AkiraBox uses its undocumented guest website upload flow, which may change. It accepts one non-empty file up to 5 GiB (5,368,709,120 bytes), not folders. Guest links expire after 7 days without a download.
- GoFile and StreamTape accept folders. StreamTape accepts video files only. BuzzHeavier, VikingFile, Filester, FileMirage, Transfer.it, storage.to, and Filebin accept single files, not folders. FileMirage uses its undocumented website upload flow and may change. Transfer.it uses the community maintained `transferit-py` client.
- storage.to's free tier supports files up to 25 GB and expires uploads. Anonymous uploads have daily file and bandwidth quotas. `STORAGETO_API_KEY` optionally attaches uploads to an account.
- Filebin and storage.to share links resolve for downloads. storage.to resolution uses its website download flow and fails when Cloudflare or Turnstile requires a challenge. Signed download URLs may expire while tasks are queued.
- `GOFILE_API_KEY`, `PIXELDRAIN_API_KEY`, `BUZZHEAVIER_API_KEY`, `STREAMTAPE_CREDENTIALS` (`login:key`), `VIKINGFILE_API_KEY` (user hash), `FILESTER_API_KEY`, and `FILEMIRAGE_API_KEY` in `config.env` are shared fallbacks. Previously saved user credentials take precedence. Shared credentials do not enable hosts automatically. Enable each host in User Settings for multi-host uploads.
- PixelDrain uploads accept an HTTP 201 file-info response even when the `success` field is absent. A file ID is still required.
- Other `-up` destinations are `gd` (`GDRIVE_ID`), `rc` (`RCLONE_PATH`), `rcl` (select an rclone path), and `remote:path` or `mrcc:remote:path` for owner or user rclone configurations.

</details>

## License and contributing

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for the full text.

Current version: `v2.0.0-x0` (see `bot/version.py`).
