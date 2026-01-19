import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

import database as db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
    print("Error: BOT_TOKEN not found in .env file")
    exit(1)

# In-memory state for active problems (current problem being solved)
user_state = {}


# ============ Start Command ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)

    await update.message.reply_text(
        "🧪 *Chemistry Practice Bot*\n\n"
        "Commands:\n"
        "/categories - Browse all categories\n"
        "/topics - View topics in current category\n"
        "/practice - Get a problem\n"
        "/hint - Get a hint\n"
        "/stats - Your progress\n"
        "/help - Show this message",
        parse_mode="Markdown"
    )


# ============ Categories ============

async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = db.get_all_categories()

    if not cats:
        await update.message.reply_text("No categories available yet.")
        return

    keyboard = []
    for cat in cats:
        keyboard.append([InlineKeyboardButton(
            f"{cat.icon} {cat.name}",
            callback_data=f"cat_{cat.id}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 *Choose a category:*", reply_markup=reply_markup, parse_mode="Markdown")


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    topics = db.get_topics_by_category(category_id)

    if not topics:
        await query.edit_message_text("No topics in this category yet.")
        return

    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(
            f"{topic.icon} {topic.name}",
            callback_data=f"topic_{topic.id}"
        )])

    keyboard.append([InlineKeyboardButton("« Back to Categories", callback_data="back_cats")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    cat = db.get_category_by_id(category_id)
    await query.edit_message_text(
        f"📂 *{cat.name}*\nChoose a topic:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    topic_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id

    db.set_user_topic(user_id, topic_id)
    topic = db.get_topic_by_id(topic_id)

    problems = db.get_problems_by_topic(topic_id)
    solved = db.get_solved_problem_ids(user_id, topic_id)

    await query.edit_message_text(
        f"✅ Topic set to *{topic.name}*\n\n"
        f"Problems: {len(problems)}\n"
        f"Solved: {len(solved)}\n\n"
        "Use /practice to start!",
        parse_mode="Markdown"
    )


async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cats = db.get_all_categories()
    keyboard = []
    for cat in cats:
        keyboard.append([InlineKeyboardButton(
            f"{cat.icon} {cat.name}",
            callback_data=f"cat_{cat.id}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📚 *Choose a category:*", reply_markup=reply_markup, parse_mode="Markdown")


# ============ Topics Command ============

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await categories(update, context)


# ============ Practice ============

async def practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = db.get_user_topic(user_id)

    if not topic:
        await update.message.reply_text(
            "Please select a topic first using /categories"
        )
        return

    # Get problems user hasn't solved yet
    solved_ids = db.get_solved_problem_ids(user_id, topic.id)
    problem = db.get_random_problem(topic.id, exclude_ids=solved_ids)

    if not problem:
        # If all solved, allow retrying any problem
        problem = db.get_random_problem(topic.id)
        if not problem:
            await update.message.reply_text("No problems available for this topic.")
            return
        await update.message.reply_text("🎉 You've solved all problems! Here's one to review:")

    user_state[user_id] = {
        "problem_id": problem.id,
        "hint_index": 0
    }

    difficulty_stars = "⭐" * problem.difficulty
    await update.message.reply_text(
        f"🧪 *Problem* ({difficulty_stars})\n\n{problem.question}",
        parse_mode="Markdown"
    )


# ============ Hint ============

async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if not state:
        await update.message.reply_text("Start a problem first using /practice")
        return

    problem = db.get_problem_by_id(state["problem_id"])
    hints = problem.hints or []
    idx = state["hint_index"]

    if idx >= len(hints):
        await update.message.reply_text("No more hints available.")
        return

    await update.message.reply_text(f"💡 *Hint {idx + 1}:* {hints[idx]}", parse_mode="Markdown")
    state["hint_index"] += 1

    # Record hint usage
    db.record_attempt(user_id, problem.id, hint_used=True)


# ============ Answer Handler ============

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if not state:
        return

    problem = db.get_problem_by_id(state["problem_id"])

    try:
        user_answer = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a numeric answer.")
        return

    correct = problem.answer
    tol = problem.tolerance

    if abs(user_answer - correct) <= tol:
        steps = problem.steps or []
        steps_text = "\n".join(f"• {s}" for s in steps)

        await update.message.reply_text(
            f"✅ *Correct!*\n\n*Solution steps:*\n{steps_text}",
            parse_mode="Markdown"
        )

        # Record success
        db.record_attempt(user_id, problem.id, solved=True)
        user_state.pop(user_id, None)
    else:
        # Record attempt
        db.record_attempt(user_id, problem.id)

        common_errors = problem.common_errors or {}
        error_msg = common_errors.get(
            str(user_answer),
            "❌ Incorrect. Try again or use /hint"
        )
        await update.message.reply_text(error_msg)


# ============ Stats ============

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_stats = db.get_user_stats(user_id)

    if not user_stats:
        await update.message.reply_text("No stats yet. Start practicing with /practice!")
        return

    await update.message.reply_text(
        f"📊 *Your Statistics*\n\n"
        f"Problems solved: {user_stats['problems_solved']}\n"
        f"Total attempts: {user_stats['total_attempts']}\n"
        f"Hints used: {user_stats['total_hints_used']}",
        parse_mode="Markdown"
    )


# ============ Help ============

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ============ Callback Router ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("cat_"):
        await category_callback(update, context)
    elif data.startswith("topic_"):
        await topic_callback(update, context)
    elif data == "back_cats":
        await back_to_categories(update, context)


# ============ Main ============

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("categories", categories))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("practice", practice))
    app.add_handler(CommandHandler("hint", hint))
    app.add_handler(CommandHandler("stats", stats))

    # Callbacks
    app.add_handler(CallbackQueryHandler(button_callback))

    # Answer handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
