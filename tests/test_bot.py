"""Drive the bot handlers with fake Telegram updates, the way a student would."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import bot
import database as db

USER_ID = 7_000_000_002


def fake_update(text=None, callback=None):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    query = None
    if callback:
        query = SimpleNamespace(data=callback, answer=AsyncMock(), edit_message_text=AsyncMock())
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=USER_ID, username="student", first_name="Aidana"),
        effective_message=message,
        message=message,
        callback_query=query,
    ), message, query


def run(handler, update):
    asyncio.run(handler(update, None))


def last_reply(message):
    return message.reply_text.call_args.args[0]


def choose_topic(name):
    topic = db.get_topic_by_name(name)
    update, message, query = fake_update(callback=f"topic_{topic.id}")
    run(bot.button_callback, update)
    problem, _ = db.get_current_problem(USER_ID)
    return problem, message


def test_choosing_a_topic_sends_a_problem():
    problem, message = choose_topic("Stoichiometry")
    assert problem is not None
    assert "Stoichiometry" in last_reply(message)


def test_correct_answer_with_comma_and_unit():
    problem, _ = choose_topic("Solutions")
    answer_text = f"{problem.answer:g}".replace(".", ",") + f" {problem.unit or ''}"
    update, message, _ = fake_update(text=answer_text)
    run(bot.handle_answer, update)

    assert "Correct" in last_reply(message)
    assert db.get_current_problem(USER_ID) == (None, 0)
    assert db.get_user_stats(USER_ID)["problems_solved"] == 1


def test_wrong_answer_gives_targeted_feedback():
    problem, _ = choose_topic("Atomic Structure")
    while not problem.common_errors:
        update, _, _ = fake_update(callback="skip")
        run(bot.button_callback, update)
        problem, _ = db.get_current_problem(USER_ID)

    wrong, feedback = next(iter(problem.common_errors.items()))
    update, message, _ = fake_update(text=wrong)
    run(bot.handle_answer, update)
    assert bot.e(feedback) in last_reply(message)
    assert db.get_current_problem(USER_ID)[0].id == problem.id


def test_non_number_is_rejected_without_counting_an_attempt():
    problem, _ = choose_topic("Redox")
    update, message, _ = fake_update(text="no idea")
    run(bot.handle_answer, update)
    assert "Please enter a number" in last_reply(message)
    assert db.get_user_progress(USER_ID, problem.id) is None


def test_solution_button_reveals_answer_and_ends_problem():
    problem, _ = choose_topic("Kinetics")
    update, message, _ = fake_update(callback="solution")
    run(bot.button_callback, update)
    assert f"{problem.answer:g}" in last_reply(message)
    assert db.get_current_problem(USER_ID) == (None, 0)


def test_problem_text_is_html_escaped():
    problem, message = choose_topic("Thermochemistry")
    assert "<b>" in last_reply(message)
    assert "<" not in bot.e("a < b")
