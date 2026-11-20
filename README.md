# Link Stats: `linkstats`

A [ChaCC API](https://pypi.org/project/chacc-api/) module that adds **click analytics** to [`shortlinks`](https://github.com/<owner>/shortlinks).

For every short link, it answers these questions:

- How many people clicked it, and how many of them were different visitors?
- On which days did they click?
- Where did they come from: Twitter, a newsletter, or a direct visit?
- Which browsers or tools did they use?

> **This module requires `shortlinks`.** Install `shortlinks` first. ChaCC refuses to install `linkstats` without it.

---

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [API reference](#api-reference)
- [Database](#database)
- [Configuration](#configuration)
- [Module lifecycle](#module-lifecycle)
- [Development](#development)
- [Notes and limitations](#notes-and-limitations)

---

## How it works

```text
  visitor ──GET /api/shortlinks/github──▶  shortlinks ──307──▶  https://github.com
                                               │
                                               │ visit event (after the response is sent)
                                               ▼
                                          linkstats ──▶ linkstats_clicks table
                                               ▲
  you ─────GET /api/linkstats/github───────────┘   totals, by day, referers, browsers
```

1. **The dependency is declared** in `module_meta.json`:
   ```json
   "module_dependencies": { "required": ["shortlinks"], "optional": [] }
   ```
2. **ChaCC loads modules in dependency order** (`shortlinks` → `linkstats`), so `shortlinks` has registered its services before `linkstats` starts.
3. **At startup, `linkstats` registers a visit listener** through the `shortlinks.add_visit_listener` service. It never imports `shortlinks` code.
4. **Every redirect stores one row** in `linkstats_clicks`. Recording happens after the redirect has been sent, so it never slows the visitor down.
5. **Codes are turned into links** through the `shortlinks.get_by_code` service.

Short links keep working with or without `linkstats`. Removing it only stops the counting.

---

## Requirements

| | |
|---|---|
| ChaCC API | `>= 1.0.0` (tested with `1.0.0b6`) |
| Modules | **`shortlinks`** (required) |
| Database | SQLite (default) or PostgreSQL, using the server's configured connection |
| Python packages | none beyond ChaCC itself |

---

## Installation

A new module is loaded when the server starts, so **every install ends with a server restart**. Always install `shortlinks` first.

### Option A: from GitHub with the CLI (recommended)

Run this from your ChaCC project folder:

```bash
chacc install <owner>/shortlinks@v0.1.0
chacc install <owner>/linkstats@v0.1.0
# restart the server
```

For private repos, export `GITHUB_TOKEN` (or `CHACC_GIT_TOKEN`) first.

If `shortlinks` is missing, the second command fails and nothing is installed:

```text
Install failed: 'linkstats' requires module(s) that are not installed in .../.modules_installed:
  - shortlinks
Install them first, then install this module again.
```

### Option B: through the API, on a running server

Build both packages from **fresh clones**. `chacc build` packs everything in the folder, so a working copy would also include `.git` and caches.

```bash
git clone --depth 1 --branch v0.1.0 https://github.com/<owner>/shortlinks.git
git clone --depth 1 --branch v0.1.0 https://github.com/<owner>/linkstats.git
chacc build shortlinks && chacc build linkstats
```

```bash
BASE=http://localhost:8085/api

curl -F file=@linkstats.chacc $BASE/modules/        # wrong order on purpose
# 409 {"detail":"Module 'linkstats' requires module(s) that are not installed: shortlinks. ...",
#      "missing_dependencies":{"required":["shortlinks"],"optional":[]}}

curl -F file=@shortlinks.chacc $BASE/modules/       # 200
curl -F file=@linkstats.chacc  $BASE/modules/       # 200
curl -X POST $BASE/system/restart                   # 202
```

`chacc deploy <file>.chacc --restart` does the upload and restart in one step.

### Option C: for development

```bash
chacc install <owner>/shortlinks --dev
chacc install <owner>/linkstats --dev
chacc run server --dev
```

### Check that it's loaded

```bash
curl $BASE/modules/graph
```
```json
{
  "load_order": ["shortlinks", "linkstats"],
  "edges": [{"from": "linkstats", "to": "shortlinks", "kind": "required", "satisfied": true}]
}
```

```bash
curl $BASE/shortlinks/_listeners
# {"listeners": ["linkstats"]}
```

---

## Quick start

```bash
BASE=http://localhost:8085/api

# A short link to track
curl -X POST $BASE/shortlinks -H 'content-type: application/json' \
     -d '{"url": "https://github.com", "code": "github"}'

# Some visits, from different places and browsers
curl -s -o /dev/null $BASE/shortlinks/github
curl -s -o /dev/null -e "https://www.twitter.com/post/1" \
     -A "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0" $BASE/shortlinks/github
curl -s -o /dev/null -e "https://newsletter.example.com/4" \
     -A "Mozilla/5.0 AppleWebKit/537.36 Chrome/120.0 Safari/537.36" $BASE/shortlinks/github

# The stats
curl $BASE/linkstats/github
```
```json
{
  "code": "github",
  "target_url": "https://github.com/",
  "total_clicks": 3,
  "unique_visitors": 1,
  "first_click": "2026-11-20T07:02:59.921350",
  "last_click": "2026-11-20T07:02:59.940654",
  "by_day": [{"day": "2026-11-20", "clicks": 3}],
  "top_referers": [
    {"name": "direct", "clicks": 1},
    {"name": "newsletter.example.com", "clicks": 1},
    {"name": "twitter.com", "clicks": 1}
  ],
  "top_agents": [
    {"name": "chrome", "clicks": 1},
    {"name": "curl", "clicks": 1},
    {"name": "firefox", "clicks": 1}
  ]
}
```

---

## API reference

All routes are mounted under **`/api/linkstats`**. They are also listed in the server's interactive docs at `/docs`.

### `GET /api/linkstats/{code}`: statistics for one link

| Query parameter | Default | Range | Description |
|---|---|---|---|
| `top` | `5` | 1–50 | how many referers and browsers to list |

| Response field | Description |
|---|---|
| `code`, `target_url` | the link |
| `total_clicks` | all recorded clicks |
| `unique_visitors` | distinct visitor IP hashes |
| `first_click`, `last_click` | UTC timestamps, or `null` if there are no clicks yet |
| `by_day` | `[{day, clicks}]`, oldest first (UTC days) |
| `top_referers` | `[{name, clicks}]`. `name` is the referring site's host without `www.`, or `direct` |
| `top_agents` | `[{name, clicks}]`. `name` is a browser family, see the [list below](#browser-families) |

`404` if the code is unknown or the link was deleted.

### `GET /api/linkstats/{code}/recent`: latest clicks

| Query parameter | Default | Range |
|---|---|---|
| `limit` | `20` | 1–200 |

```json
[
  {
    "at": "2026-11-20T07:02:59.940654",
    "agent_family": "chrome",
    "referer_host": "twitter.com",
    "user_agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
  }
]
```

### `GET /api/linkstats/top`: most clicked links

| Query parameter | Default | Range |
|---|---|---|
| `limit` | `5` | 1–100 |

```json
[{"code": "github", "target_url": "https://github.com/", "clicks": 3, "unique_visitors": 1}]
```

`target_url` is `null` for links that have since been deleted. Their clicks still count.

### Browser families

The `user_agent` header is sorted into one of these families. The rules are checked in this order, so Edge isn't counted as Chrome.

`bot` · `curl` · `httpie` · `python` · `postman` · `edge` · `opera` · `chrome` · `firefox` · `safari` · `other` · `unknown` (no user agent sent)

---

## Database

One table, created automatically at startup by ChaCC's migrations (`MIGRATION_MODE=auto`).

**`linkstats_clicks`**: one row per redirect

| Column | Type | Notes |
|---|---|---|
| `id` | integer | primary key |
| `link_id` | integer | indexed. Points to `shortlinks_links.id`. |
| `code` | varchar(32) | indexed. Copied from the link so ranking needs no join. |
| `user_agent` | varchar(512) | raw header, nullable |
| `agent_family` | varchar(32) | e.g. `chrome`, `curl`, `bot` |
| `referer` | varchar(1024) | raw header, nullable |
| `referer_host` | varchar(255) | e.g. `twitter.com`, or `direct` |
| `ip_hash` | varchar(64) | salted SHA-256 of the visitor's IP. **Raw IPs are never stored.** |
| `created_at` | datetime | time of the click (UTC) |
| `uuid`, `updated_at`, `deleted_at` | | inherited from `ChaCCBaseModel` |

**How the two tables are linked:** `link_id` is declared as a foreign key in the model. ChaCC's SQLite migrations create the table **without** that constraint, so the relationship is enforced in code instead: every lookup goes through `shortlinks.get_by_code`.

Uninstalling either module **does not drop its table**. Data survives a reinstall.

---

## Configuration

Set in the ChaCC project's `.env` file. ChaCC prefixes module settings with the module name.

| Variable | Default | Purpose |
|---|---|---|
| `LINKSTATS_IP_SALT` | `linkstats-demo-salt` | Salt used to hash visitor IPs. **Set your own value in production**, otherwise the hashes could be reversed by trying every IP address. Changing it resets the unique-visitor counts. |

---

## Module lifecycle

These were checked against a ChaCC `1.0.0b6` server in production mode:

| Action | Result |
|---|---|
| Install `linkstats` without `shortlinks` | **Refused**: `409` through the API, an error through `chacc install`. Nothing is installed. |
| Disable `linkstats` | Short links keep redirecting (`307`). `/api/linkstats/*` returns `404`. Clicks are **not recorded** while it is disabled. |
| Enable it again | Stats come back with all earlier clicks. |
| Disable or uninstall `shortlinks` | Allowed, with a warning. `linkstats` is **not loaded** after the restart. |
| Enable `linkstats` while `shortlinks` is missing | **Refused** with `409`. |
| Reinstall `shortlinks`, then enable `linkstats` | Everything is back, including old clicks. |

Manage the module with these endpoints:

```bash
curl -X POST   $BASE/modules/linkstats/disable
curl -X POST   $BASE/modules/linkstats/enable
curl -X DELETE $BASE/modules/linkstats/uninstall
curl -X POST   $BASE/system/restart        # needed after each of the above
```

---

## Development

```text
linkstats/
├── module_meta.json          # declares the required "shortlinks" dependency
├── requirements.txt          # no extra packages
└── linkstats_src/
    ├── main.py               # setup_plugin(): registers the visit listener
    ├── models.py             # Click table and response schemas
    ├── routes.py             # the stats endpoints
    ├── service.py            # browser/referer parsing, IP hashing, click recording
    └── tests/test_module.py
```

Run the tests from the module folder, using the ChaCC project's virtualenv:

```bash
pytest linkstats_src/tests -v
```

The tests cover browser detection, referer parsing and IP hashing.

---

## Notes and limitations

- **Only clicks made while `linkstats` is running are counted.** There's no backfill. The `hits` counter in `shortlinks` counts every redirect.
- **Days and timestamps are UTC.**
- **"Unique visitors" means distinct IP addresses.** People behind the same network or proxy count as one.
- **Bots are recorded too** (as `agent_family: "bot"`), not filtered out.
- **Behind a reverse proxy,** forward the client IP (e.g. uvicorn's `--proxy-headers`). Otherwise every visitor shares the proxy's IP.

## License

MIT
