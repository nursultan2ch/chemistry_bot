import html
import logging
import os
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

import database as db
from answers import parse_answer, is_correct, match_common_error

load_dotenv()

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("chemistry_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")

COMMANDS = [
    ("categories", "Choose a category and topic"),
    ("practice", "Get a problem"),
    ("hint", "Get a hint for the current problem"),
    ("skip", "Skip the current problem"),
    ("stats", "Your progress"),
    ("leaderboard", "Top solvers"),
    ("help", "Show help"),
]

e = html.escape


def problem_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Hint", callback_data="hint"),
        InlineKeyboardButton("⏭ Skip", callback_data="skip"),
        InlineKeyboardButton("📖 Solution", callback_data="solution"),
    ]])


def next_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("➡️ Next problem", callback_data="next"),
        InlineKeyboardButton("📚 Change topic", callback_data="back_cats"),
    ]])


def format_steps(problem):
    steps = problem.steps or []
    return "\n".join(f"{i}. {e(s)}" for i, s in enumerate(steps, start=1))


def format_answer(problem):
    unit = f" {e(problem.unit)}" if problem.unit else ""
    return f"{problem.answer:g}{unit}"


async def reply(update: Update, text: str, **kwargs):
    """Reply to a command or to a button press"""
    message = update.effective_message
    await message.reply_text(text, parse_mode=ParseMode.HTML, **kwargs)


# ============ Start / Help ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)

    lines = "\n".join(f"/{name} - {e(desc)}" for name, desc in COMMANDS)
    await reply(
        update,
        "🧪 <b>Chemistry Practice Bot</b>\n\n"
        "Solve olympiad-style chemistry problems with hints and step-by-step solutions.\n"
        "Type your answer as a number, e.g. <code>0.5</code>, <code>0,5</code>, "
        "<code>14.6 g</code> or <code>3.01e23</code>.\n\n"
        f"{lines}\n\n"
        "Start with /categories."
    )


# ============ Categories ============

def categories_keyboard():
    cats = db.get_all_categories()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{cat.icon} {cat.name}", callback_data=f"cat_{cat.id}")]
        for cat in cats
    ]) if cats else None


async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.get_or_create_user(update.effective_user.id, update.effective_user.username,
                          update.effective_user.first_name)
    keyboard = categories_keyboard()
    if not keyboard:
        await reply(update, "No categories available yet.")
        return
    await reply(update, "📚 <b>Choose a category:</b>", reply_markup=keyboard)


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: int):
    query = update.callback_query
    cat = db.get_category_by_id(category_id)
    topics = db.get_topics_by_category(category_id)

    if not cat or not topics:
        await query.edit_message_text("No topics in this category yet.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                          "« Back to Categories", callback_data="back_cats")]]))
        return

    keyboard = []
    for topic in topics:
        count = db.count_problems_by_topic(topic.id)
        keyboard.append([InlineKeyboardButton(
            f"{topic.icon} {topic.name} ({count})",
            callback_data=f"topic_{topic.id}"
        )])
    keyboard.append([InlineKeyboardButton("« Back to Categories", callback_data="back_cats")])

    await query.edit_message_text(
        f"📂 <b>{e(cat.name)}</b>\nChoose a topic:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, topic_id: int):
    query = update.callback_query
    user_id = update.effective_user.id

    topic = db.get_topic_by_id(topic_id)
    if not topic:
        await query.edit_message_text("That topic no longer exists. Use /categories.")
        return

    db.get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name)
    db.set_user_topic(user_id, topic_id)

    total = db.count_problems_by_topic(topic_id)
    solved = len(db.get_solved_problem_ids(user_id, topic_id))

    await query.edit_message_text(
        f"✅ Topic set to <b>{e(topic.name)}</b>\n\n"
        f"Solved: {solved}/{total}",
        parse_mode=ParseMode.HTML
    )
    await send_problem(update, context)


async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = categories_keyboard()
    await update.callback_query.edit_message_text(
        "📚 <b>Choose a category:</b>", reply_markup=keyboard, parse_mode=ParseMode.HTML
    )


# ============ Practice ============

async def send_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = db.get_user_topic(user_id)

    if not topic:
        await reply(update, "Please select a topic first using /categories")
        return

    # Prefer problems the user hasn't solved yet
    solved_ids = db.get_solved_problem_ids(user_id, topic.id)
    current, _ = db.get_current_problem(user_id)
    exclude = solved_ids + ([current.id] if current else [])
    problem = db.get_random_problem(topic.id, exclude_ids=exclude)

    if not problem:
        problem = db.get_random_problem(topic.id, exclude_ids=[current.id] if current else None) \
            or db.get_random_problem(topic.id)
        if not problem:
            await reply(update, "No problems available for this topic yet.")
            return
        await reply(update, "🎉 You've solved every problem in this topic! Here's one to review:")

    db.start_problem(user_id, problem.id)

    difficulty_stars = "⭐" * (problem.difficulty or 1)
    unit = f"\n\n<i>Answer in {e(problem.unit)}</i>" if problem.unit else ""
    await reply(
        update,
        f"🧪 <b>{e(topic.name)}</b> {difficulty_stars}\n\n{e(problem.question)}{unit}",
        reply_markup=problem_keyboard()
    )


async def practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.get_or_create_user(update.effective_user.id, update.effective_user.username,
                          update.effective_user.first_name)
    await send_problem(update, context)


# ============ Hint / Skip / Solution ============

async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx, text = db.next_hint(update.effective_user.id)

    if idx is None:
        await reply(update, "Start a problem first using /practice")
    elif text is None:
        await reply(update, "No more hints. Tap 📖 Solution to see the full answer.",
                    reply_markup=problem_keyboard())
    else:
        await reply(update, f"💡 <b>Hint {idx + 1}:</b> {e(text)}")


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current, _ = db.get_current_problem(update.effective_user.id)
    if not current:
        await reply(update, "Start a problem first using /practice")
        return
    await send_problem(update, context)


async def solution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    problem, _ = db.get_current_problem(user_id)
    if not problem:
        await reply(update, "Start a problem first using /practice")
        return

    db.clear_current_problem(user_id)
    await reply(
        update,
        f"📖 <b>Answer:</b> {format_answer(problem)}\n\n<b>Solution:</b>\n{format_steps(problem)}",
        reply_markup=next_keyboard()
    )


# ============ Answer Handler ============

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    problem, _ = db.get_current_problem(user_id)

    if not problem:
        await reply(update, "Use /practice to get a problem, or /help to see all commands.")
        return

    value = parse_answer(update.message.text)
    if value is None:
        await reply(update, "Please enter a number, e.g. <code>0.5</code> or <code>3.01e23</code>.")
        return

    if is_correct(value, problem.answer, problem.tolerance):
        db.record_attempt(user_id, problem.id, solved=True)
        db.clear_current_problem(user_id)
        await reply(
            update,
            f"✅ <b>Correct!</b> {format_answer(problem)}\n\n<b>Solution:</b>\n{format_steps(problem)}",
            reply_markup=next_keyboard()
        )
    else:
        db.record_attempt(user_id, problem.id)
        feedback = match_common_error(value, problem.common_errors, problem.tolerance)
        message = f"❌ {e(feedback)}" if feedback else "❌ Incorrect. Try again, or use the buttons below."
        await reply(update, message, reply_markup=problem_keyboard())


# ============ Stats ============

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_stats = db.get_user_stats(update.effective_user.id)

    if not user_stats or not user_stats["total_attempts"]:
        await reply(update, "No stats yet. Start practicing with /practice!")
        return

    await reply(
        update,
        "📊 <b>Your Statistics</b>\n\n"
        f"Problems solved: {user_stats['problems_solved']}/{user_stats['total_problems']}\n"
        f"Solved first try, no hints: {user_stats['first_try']}\n"
        f"Total attempts: {user_stats['total_attempts']}\n"
        f"Hints used: {user_stats['total_hints_used']}"
    )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.get_leaderboard()
    if not rows:
        await reply(update, "Nobody has solved a problem yet. Be the first with /practice!")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"{medals[i] if i < 3 else f'{i + 1}.'} {e(name)}: {count}" for i, (name, count) in enumerate(rows)]
    await reply(update, "🏆 <b>Leaderboard</b>\n\n" + "\n".join(lines))


# ============ Callback Router ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("cat_"):
        await category_callback(update, context, int(data.removeprefix("cat_")))
    elif data.startswith("topic_"):
        await topic_callback(update, context, int(data.removeprefix("topic_")))
    elif data == "back_cats":
        await back_to_categories(update, context)
    elif data == "hint":
        await hint(update, context)
    elif data in ("skip", "next"):
        await send_problem(update, context)
    elif data == "solution":
        await solution(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Error while handling update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("⚠️ Something went wrong. Please try again.")


async def post_init(app: Application):
    await app.bot.set_my_commands([BotCommand(name, desc) for name, desc in COMMANDS])


# ============ Main ============

def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        log.error("BOT_TOKEN is not set (see .env.example)")
        sys.exit(1)

    db.seed_initial_data()
    added, _ = db.import_problems()
    if added:
        log.info("Imported %d new problems", added)

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("categories", categories))
    app.add_handler(CommandHandler("topics", categories))
    app.add_handler(CommandHandler("practice", practice))
    app.add_handler(CommandHandler("hint", hint))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("solution", solution))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))

    # Callbacks
    app.add_handler(CallbackQueryHandler(button_callback))

    # Answer handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.add_error_handler(error_handler)

    log.info("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
