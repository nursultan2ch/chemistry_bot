# Chemistry Practice Bot

A Telegram bot for practicing chemistry problems with an admin panel for content management.

## Features

- **Telegram Bot**: Interactive chemistry practice with hints, step-by-step solutions, and progress tracking
- **Admin Panel**: Web-based interface to manage categories, topics, and problems
- **User Progress**: Track solved problems, attempts, and hints used
- **Categories & Topics**: Organized content structure (General Chemistry, Organic, Inorganic, Physical)

## Prerequisites

- Python 3.10+
- PostgreSQL
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Installation

1. **Clone the repository**
   ```bash
   cd Chemistry_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create `.env` file** (or edit existing one):
   ```env
   # Telegram Bot Token (from @BotFather)
   BOT_TOKEN=your_telegram_bot_token_here

   # PostgreSQL Database URL
   DATABASE_URL=postgresql://username@localhost/chemistry_bot

   # Admin Panel Credentials
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_secure_password
   ADMIN_PORT=5001

   # Flask Secret Key
   SECRET_KEY=your_random_secret_key

   # Optional: Enable Flask debug mode
   FLASK_DEBUG=false
   ```

2. **Get a Telegram Bot Token**:
   - Open Telegram and search for [@BotFather](https://t.me/BotFather)
   - Send `/newbot` and follow instructions
   - Copy the token to your `.env` file

## Database Setup

### Option 1: Local PostgreSQL

```bash
# Create the database
createdb chemistry_bot

# Seed initial data
python database.py
```

### Option 2: Docker PostgreSQL

```bash
# Start PostgreSQL container
docker run -d \
  --name chemistry_db \
  -e POSTGRES_DB=chemistry_bot \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://postgres:postgres@localhost/chemistry_bot

# Seed initial data
python database.py
```

## Running the Application

### Start the Bot

```bash
source venv/bin/activate
python bot.py
```

### Start the Admin Panel

```bash
source venv/bin/activate
python admin.py
```

Open **http://localhost:5001** in your browser.

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/categories` | Browse all categories |
| `/topics` | View topics (same as categories) |
| `/practice` | Get a chemistry problem |
| `/hint` | Get a hint for current problem |
| `/stats` | View your progress statistics |
| `/help` | Show help message |

## Admin Panel

Access the admin panel at `http://localhost:5001`

### Managing Content

1. **Categories**: Main subject areas (e.g., General Chemistry, Organic Chemistry)
2. **Topics**: Subtopics within categories (e.g., Stoichiometry, Mole Concept)
3. **Problems**: Individual practice problems with:
   - Question text
   - Numeric answer with tolerance
   - Difficulty level (1-3 stars)
   - Solution steps (JSON list)
   - Hints (JSON list)
   - Common errors (JSON dict)

### Adding a Problem

1. Go to **Content > Problems > Create**
2. Fill in:
   - **Topic**: Select from dropdown
   - **Question**: The problem text
   - **Answer**: Numeric answer (e.g., `0.5`)
   - **Tolerance**: Acceptable error margin (e.g., `0.01`)
   - **Difficulty**: 1 (easy), 2 (medium), 3 (hard)
   - **Steps**: `["Step 1", "Step 2", "Step 3"]`
   - **Hints**: `["Hint 1", "Hint 2"]`
   - **Common Errors**: `{"1.0": "You used wrong molar mass"}`

## Project Structure

```
Chemistry_bot/
├── bot.py          # Telegram bot with database integration
├── main.py         # Simple bot version (no database)
├── admin.py        # Flask admin panel
├── database.py     # Database operations
├── models.py       # SQLAlchemy models
├── problems.json   # Sample problems (for main.py)
├── requirements.txt
├── .env            # Configuration (not in git)
└── venv/           # Virtual environment
```

## Troubleshooting

### "role 'postgres' does not exist"
You have local PostgreSQL. Use your username:
```env
DATABASE_URL=postgresql://your_username@localhost/chemistry_bot
```

### "Port 5000 is in use"
macOS AirPlay uses port 5000. Change admin port:
```env
ADMIN_PORT=5001
```

### "Conflict: terminated by other getUpdates request"
Multiple bot instances running. Kill all:
```bash
pkill -f "python.*bot.py"
```

### Bot not responding
1. Check bot is running: `ps aux | grep bot.py`
2. Check logs for errors
3. Ensure BOT_TOKEN is correct

## License

MIT
