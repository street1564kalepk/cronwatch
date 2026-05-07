# cronwatch

Lightweight daemon that monitors cron job execution times and sends alerts on unexpected delays or failures.

## Installation

```bash
pip install cronwatch
```

## Usage

Define your monitored jobs in a `cronwatch.yaml` config file:

```yaml
jobs:
  daily-backup:
    schedule: "0 2 * * *"
    timeout: 300
    alert: email

  sync-data:
    schedule: "*/15 * * * *"
    timeout: 60
    alert: slack

alerts:
  email:
    to: ops@example.com
    smtp_host: smtp.example.com
  slack:
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Start the daemon:

```bash
cronwatch start --config cronwatch.yaml
```

Wrap an existing cron command to report its status:

```bash
cronwatch run --job daily-backup -- /usr/local/bin/backup.sh
```

cronwatch will track execution time, detect missed runs, and fire alerts if a job exceeds its timeout or fails to execute on schedule.

## Commands

| Command | Description |
|---------|-------------|
| `cronwatch start` | Start the monitoring daemon |
| `cronwatch stop` | Stop the running daemon |
| `cronwatch status` | Show status of all monitored jobs |
| `cronwatch run` | Wrap a command and report its result |
| `cronwatch check` | Validate your config file |

## Alerts

Supported alert channels: `email`, `slack`, `webhook`. Configure credentials under the `alerts` section of your config file.

## License

MIT © cronwatch contributors
