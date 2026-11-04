import json

import database as db
from answers import is_correct


def make_user(telegram_id=7_000_000_001):  # larger than a 32-bit int, like real Telegram ids
    db.get_or_create_user(telegram_id, "student", "Aidana")
    return telegram_id


def test_seed_and_import_are_idempotent():
    topics_before = sum(len(db.get_topics_by_category(c.id)) for c in db.get_all_categories())
    db.seed_initial_data()
    added, skipped = db.import_problems()
    topics_after = sum(len(db.get_topics_by_category(c.id)) for c in db.get_all_categories())
    assert added == 0 and skipped > 0
    assert topics_before == topics_after == 12


def test_every_topic_has_problems():
    for category in db.get_all_categories():
        for topic in db.get_topics_by_category(category.id):
            assert db.count_problems_by_topic(topic.id) >= 3, topic.name


def test_problem_file_is_consistent():
    with open(db.PROBLEMS_FILE, encoding="utf-8") as f:
        problems = json.load(f)
    for p in problems:
        assert p["steps"] and p["hints"], p["question"]
        assert 1 <= p["difficulty"] <= 3
        for wrong in p.get("common_errors", {}):
            # Feedback for a wrong answer must never fire on the right one
            assert not is_correct(float(wrong), p["answer"], p["tolerance"]), p["question"]


def test_active_problem_survives_in_db():
    user = make_user()
    topic = db.get_topic_by_name("Stoichiometry")
    db.set_user_topic(user, topic.id)
    problem = db.get_random_problem(topic.id)
    db.start_problem(user, problem.id)

    current, hint_index = db.get_current_problem(user)
    assert current.id == problem.id and hint_index == 0

    db.set_user_topic(user, db.get_topic_by_name("Redox").id)
    assert db.get_current_problem(user) == (None, 0)


def test_hints_advance_and_do_not_count_as_attempts():
    user = make_user()
    topic = db.get_topic_by_name("Stoichiometry")
    problem = db.get_random_problem(topic.id)
    db.start_problem(user, problem.id)

    seen = []
    while True:
        idx, text = db.next_hint(user)
        if text is None:
            break
        seen.append(text)
    assert seen == problem.hints
    assert idx == len(problem.hints)

    progress = db.get_user_progress(user, problem.id)
    assert progress.hints_used == len(problem.hints)
    assert progress.attempts == 0


def test_solving_updates_stats_and_leaderboard():
    user = make_user()
    topic = db.get_topic_by_name("Kinetics")
    problem = db.get_random_problem(topic.id)

    db.record_attempt(user, problem.id)
    db.record_attempt(user, problem.id, solved=True)
    db.record_attempt(user, problem.id, solved=True)  # re-solving doesn't double count

    stats = db.get_user_stats(user)
    assert stats["problems_solved"] == 1
    assert stats["total_attempts"] == 3
    assert stats["first_try"] == 0
    assert db.get_solved_problem_ids(user, topic.id) == [problem.id]
    assert db.get_leaderboard() == [("@student", 1)]


def test_random_problem_skips_solved():
    user = make_user()
    topic = db.get_topic_by_name("Thermochemistry")
    problems = db.get_problems_by_topic(topic.id)
    for p in problems[:-1]:
        db.record_attempt(user, p.id, solved=True)

    solved = db.get_solved_problem_ids(user, topic.id)
    for _ in range(10):
        assert db.get_random_problem(topic.id, exclude_ids=solved).id == problems[-1].id
