# Chain Wax Bot

A small home-server Telegram bot that reads cycling mileage from Strava and reminds you to wax your chain after a configurable number of kilometers.

## Features

- Reads cycling distance from the official Strava API.
- Uses Strava OAuth refresh token flow.
- Stores the latest Strava refresh token in persistent state, not in `.env`.
- Checks mileage once per day at `CHECK_TIME`.
- Keeps a monotonic `logical_total_km` odometer to survive yearly counter rollover.
- Sends at most one Telegram reminder per calendar day after the threshold is reached.
- Runs as one long-lived Python process in Docker.
- Uses a simple JSON state file, no PostgreSQL, Redis, cron, or message queue.

## Strava API Setup

1. Open https://www.strava.com/settings/api.
2. Create a Strava API application.
3. Save the `Client ID` and `Client Secret`.
4. Generate a refresh token with permission to read athlete stats.
5. Find your `STRAVA_ATHLETE_ID`.

The bot calls:

- `POST https://www.strava.com/oauth/token` to get a short-lived access token.
- `GET https://www.strava.com/api/v3/athletes/{athlete_id}/stats` to get cycling totals.

The preferred source is `all_ride_totals.distance`. If that is unavailable, the bot falls back to `ytd_ride_totals.distance`.

## Telegram Setup

1. Open Telegram and message `@BotFather`.
2. Create a bot with `/newbot`.
3. Save `TELEGRAM_BOT_TOKEN`.
4. Send any message to your new bot.
5. Get your `TELEGRAM_CHAT_ID`, for example with:

```text
https://api.telegram.org/bot<token>/getUpdates
```

The bot processes commands only from `TELEGRAM_CHAT_ID`. Other chats receive `Unauthorized` and cannot change state.

## Configuration

For local Docker usage, create `.env` from the example:

```bash
cp .env.example .env
```

Fill it in:

```dotenv
STRAVA_CLIENT_ID=12345
STRAVA_CLIENT_SECRET=...
STRAVA_REFRESH_TOKEN=...
STRAVA_ATHLETE_ID=123456

TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=123456789

CHECK_TIME=10:00
DEFAULT_INTERVAL_KM=500
TZ=Europe/Chisinau
```

Do not commit `.env`. It is ignored by Git.

## Running Locally

Build and start:

```bash
docker compose up -d --build
```

Follow logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

## Telegram Commands

- `/status` - show current mileage, last wax mileage, interval, and remaining distance.
- `/wax` - fetch current Strava mileage and save it as the latest wax mileage.
- `/wax 12910` - manually save wax mileage.
- `/wax 12910.5` - decimal values are supported.
- `/interval 450` - change the service interval. Valid range: `50-5000` km.
- `/check` - force a Strava refresh and show status.
- `/help` - show available commands.

On first startup, if `last_wax_km` is not set, reminders are not sent. Use `/wax` or `/wax <mileage>`.

## Year Rollover Handling

The service does not calculate chain service distance as:

```text
current_ytd_km - last_wax_km
```

Instead, it stores its own monotonic `logical_total_km`.

If Strava returns lifetime mileage through `all_ride_totals.distance`, that value is used as the primary source. If lifetime mileage unexpectedly decreases, the bot logs a warning and does not decrease `logical_total_km`.

If the bot has to use the yearly `ytd_ride_totals.distance` counter and the value decreases, it treats that as rollover:

- December 31: Strava reports `8123 km`.
- January 1: Strava reports `15 km`.
- `logical_total_km` becomes `8138 km`.

This means `logical_total_km` never moves backwards.

## State File

State is stored at:

```text
/app/data/state.json
```

With the default compose file, that path is mounted from:

```text
${DATA_DIR:-./data}:/app/data
```

For production deployment, set `DATA_DIR` to a persistent directory outside the GitHub Actions workspace, for example:

```text
/opt/chain-wax-bot-data
```

Example:

```json
{
  "last_strava_km": 8123.4,
  "logical_total_km": 8123.4,
  "last_wax_km": 7650.0,
  "interval_km": 500,
  "last_alert_date": "2026-09-23",
  "last_check_date": "2026-09-23",
  "strava_refresh_token": "..."
}
```

`state.json` is written atomically with a temporary file, `fsync`, and replace.

Backup:

```bash
cp data/state.json data/state.json.backup
```

## Tests

Run tests locally:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
```

Run tests through Docker:

```bash
docker compose run --rm chain-wax-bot pytest
```

## GitHub Actions

The repository includes `.github/workflows/ci.yml`.

The workflow has two jobs:

- `test` runs on GitHub-hosted runners for pushes, pull requests, and manual runs.
- `deploy` runs only after a push to `main`, and only on your self-hosted runner labeled `linux-nas`.

This is the recommended setup for a home server behind NAT: the server connects outbound to GitHub as a self-hosted runner, so GitHub does not need SSH access, public ports, port forwarding, or a public IP address.

### CI Job

The `test` job:

- installs Python dependencies with Python 3.12;
- runs `pytest`;
- builds the Docker image;
- creates a temporary dummy `.env`;
- validates `docker compose config`.

### Deployment Behind NAT

Install a GitHub Actions self-hosted runner on the home server where the bot should run.

In GitHub:

1. Open the repository.
2. Go to `Settings` -> `Actions` -> `Runners`.
3. Click `New self-hosted runner`.
4. Choose Linux.
5. Follow the commands shown by GitHub on your server.

Add the custom runner label:

```text
linux-nas
```

The deploy job uses:

```yaml
runs-on: [self-hosted, linux, linux-nas]
```

Run the runner as a service so it survives reboot. GitHub shows the exact commands, usually similar to:

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

The server needs:

- Docker installed;
- Docker Compose plugin installed;
- the runner user allowed to run Docker;
- outbound HTTPS access to GitHub.

No inbound network access to the server is required.

If the runner user cannot run Docker yet, add it to the Docker group:

```bash
sudo usermod -aG docker <runner-user>
```

Then log out and back in, or restart the runner service.

### Required GitHub Secrets

Create a GitHub Actions environment named `deploy`:

`Settings` -> `Environments` -> `New environment` -> `deploy`

Add these secrets to the `deploy` environment:

`Settings` -> `Environments` -> `deploy` -> `Environment secrets`

Required secrets:

- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN`
- `STRAVA_ATHLETE_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional repository variables:

- `CHECK_TIME`, defaults to `10:00`
- `DEFAULT_INTERVAL_KM`, defaults to `500`
- `TZ`, defaults to `Europe/Chisinau`
- `DATA_DIR`, defaults to `$HOME/chain-wax-bot-data` on the self-hosted runner

Add optional values in:

`Settings` -> `Environments` -> `deploy` -> `Environment variables`

For production, `DATA_DIR` should point to a persistent directory on the home server, for example:

```text
/opt/chain-wax-bot-data
```

The deploy job creates this directory if it does not exist and mounts it into the container as `/app/data`.

### How Deployment Works

Open a pull request as usual. The CI job will run tests and Docker build.

After the pull request is merged into `main`, GitHub starts the `deploy` job on your self-hosted runner:

1. checks out the latest `main`;
2. creates `.env` from GitHub Secrets and Variables;
3. creates `DATA_DIR` if needed;
4. runs:

```bash
docker compose up -d --build
```

You can also start the workflow manually:

`Actions` -> `CI/CD` -> `Run workflow`

Manual runs execute CI. Deployment still only runs for a `push` to `main`.

### Triggering Deployment

Merge to `main`:

```bash
git push
```

The self-hosted runner will deploy the updated container on the home server.
