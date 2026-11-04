# Chemistry Practice Bot

A Telegram bot for olympiad-style chemistry practice. Students pick a topic, solve numeric problems, and get
progressive hints, step-by-step solutions, and feedback that recognises common mistakes ("You divided by 22
instead of the molar mass"). Teachers manage the content through a web admin panel.

## Features

- **48 problems in 12 topics** across general, organic, inorganic and physical chemistry, each with hints, a
  worked solution, and difficulty from ⭐ to ⭐⭐⭐
- **Mistake-aware feedback**: wrong answers that match a known error get a targeted explanation instead of "incorrect"
- **Answers typed the way students type them**: `0,5`, `14.6 g`, `3.01e23` and `3.01 × 10^23` are all accepted
- **Inline buttons** for Hint / Skip / Solution / Next problem
- **Progress tracking**: solved count, first-try solves, hints used, and a leaderboard
- **Admin panel** (Flask-Admin) to add and edit categories, topics and problems, with a usage dashboard
- **Stateless bot process**: the active problem lives in PostgreSQL, so restarts and redeploys don't lose a student's place

## Bot Commands

| Command | Description |
|---------|-------------|
| `/categories` | Choose a category and topic |
| `/practice` | Get a problem |
| `/hint` | Next hint for the current problem |
| `/skip` | Skip to another problem |
| `/solution` | Show the answer and worked solution |
| `/stats` | Your progress |
| `/leaderboard` | Top solvers |
| `/help` | Show help |

## Architecture

```
Telegram ──▶ bot.py (python-telegram-bot, polling)
                │
                ├── answers.py   parse "0,5" / "3.01e23", tolerance check, common-error matching
                └── database.py  SQLAlchemy queries ──▶ PostgreSQL ◀── admin.py (Flask-Admin, gunicorn)
                                                         ▲
                                     data/problems.json ─┘ imported on startup, idempotent
```

| File | Purpose |
|------|---------|
| `bot.py` | Telegram handlers and inline keyboards |
| `answers.py` | Parsing and checking numeric answers |
| `database.py` | Data access, seeding, problem import |
| `models.py` | SQLAlchemy models |
| `admin.py` | Admin panel with HTTP basic auth |
| `data/problems.json` | Problem bank |
| `migrations/` | SQL for upgrading an existing database |
| `tests/` | pytest suite (SQLite in memory, no Telegram needed) |

## Quick Start (Docker)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Configure:
   ```bash
   cp .env.example .env   # then set BOT_TOKEN, POSTGRES_PASSWORD, ADMIN_PASSWORD, SECRET_KEY
   ```
   Generate a secret key with `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Run:
   ```bash
   docker compose up -d --build
   ```

The bot creates its tables and imports `data/problems.json` on first start. The admin panel listens on
`127.0.0.1:5000` only. On a server, reach it with `ssh -L 5000:localhost:5000 your-server` or put it
behind an HTTPS reverse proxy. Basic auth over plain HTTP sends the password in the clear.

## Local Development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt pytest
cp .env.example .env            # set BOT_TOKEN, ADMIN_PASSWORD, SECRET_KEY
createdb chemistry_bot
python database.py              # create tables, seed topics, import problems
python bot.py                   # in one terminal
python admin.py                 # in another; open http://localhost:5001
pytest -q
```

**Upgrading a database from the first version?** Run the migration once:
```bash
psql -d chemistry_bot -f migrations/001_state_units_bigint.sql
```

## Adding Problems

Either use **Content → Problems → Create** in the admin panel, or add entries to `data/problems.json` (or any
file with the same format) and run `python import_json.py [file]`. Problems already in the database are skipped.

```json
{
  "topic_name": "Stoichiometry",
  "question": "How many moles are in 22 g of CO₂?",
  "answer": 0.5,
  "unit": "mol",
  "tolerance": 0.01,
  "difficulty": 1,
  "hints": ["Use n = m / M"],
  "steps": ["M(CO₂) = 44 g/mol", "n = 22 / 44 = 0.5 mol"],
  "common_errors": {"1.0": "You divided by 22 instead of the molar mass 44 g/mol"}
}
```

`common_errors` maps a wrong answer to the feedback shown for it. Matching is numeric within `tolerance`, so
`"1.0"` also catches `1`, `1,0` and `1.004`. The test suite checks that no feedback can fire on the correct answer.

## Troubleshooting

- **"Conflict: terminated by other getUpdates request"**: two bot instances are polling with the same
  token. Stop the other one (`pkill -f "python.*bot.py"`, or `docker compose stop bot`).
- **"role 'postgres' does not exist"**: Homebrew PostgreSQL uses your macOS username:
  `DATABASE_URL=postgresql://your_username@localhost/chemistry_bot`.
- **Port 5000 is in use on macOS**: AirPlay uses it, so set `ADMIN_PORT=5001` for local runs.

## License

MIT
