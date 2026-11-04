import json
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import func

from models import (
    init_db, utcnow, Category, Topic, Problem, User, UserProgress
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/chemistry_bot")
PROBLEMS_FILE = os.path.join(os.path.dirname(__file__), "data", "problems.json")

engine, Session = init_db(DATABASE_URL)


@contextmanager
def get_session():
    """Context manager for database sessions"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _get_user(session, telegram_id: int):
    return session.query(User).filter(User.telegram_id == telegram_id).first()


# ============ Category Operations ============

def get_all_categories(active_only=True):
    """Get all categories"""
    with get_session() as session:
        query = session.query(Category)
        if active_only:
            query = query.filter(Category.is_active == True)
        return query.order_by(Category.order).all()


def get_category_by_id(category_id: int):
    """Get category by ID"""
    with get_session() as session:
        return session.query(Category).filter(Category.id == category_id).first()


def create_category(name: str, description: str = None, icon: str = "📚"):
    """Create a new category"""
    with get_session() as session:
        category = Category(name=name, description=description, icon=icon)
        session.add(category)
        session.flush()
        return category.id


# ============ Topic Operations ============

def get_topics_by_category(category_id: int, active_only=True):
    """Get all topics in a category"""
    with get_session() as session:
        query = session.query(Topic).filter(Topic.category_id == category_id)
        if active_only:
            query = query.filter(Topic.is_active == True)
        return query.order_by(Topic.order).all()


def get_topic_by_id(topic_id: int):
    """Get topic by ID"""
    with get_session() as session:
        return session.query(Topic).filter(Topic.id == topic_id).first()


def get_topic_by_name(name: str):
    """Get topic by name (case insensitive)"""
    with get_session() as session:
        return session.query(Topic).filter(Topic.name.ilike(name)).first()


def create_topic(category_id: int, name: str, description: str = None, icon: str = "🔬"):
    """Create a new topic"""
    with get_session() as session:
        topic = Topic(category_id=category_id, name=name, description=description, icon=icon)
        session.add(topic)
        session.flush()
        return topic.id


# ============ Problem Operations ============

def get_problems_by_topic(topic_id: int, active_only=True):
    """Get all problems for a topic"""
    with get_session() as session:
        query = session.query(Problem).filter(Problem.topic_id == topic_id)
        if active_only:
            query = query.filter(Problem.is_active == True)
        return query.all()


def count_problems_by_topic(topic_id: int):
    """Count active problems in a topic"""
    with get_session() as session:
        return session.query(Problem).filter(
            Problem.topic_id == topic_id,
            Problem.is_active == True
        ).count()


def get_random_problem(topic_id: int, exclude_ids: list = None):
    """Get a random problem from a topic, optionally excluding already solved"""
    with get_session() as session:
        query = session.query(Problem).filter(
            Problem.topic_id == topic_id,
            Problem.is_active == True
        )
        if exclude_ids:
            query = query.filter(Problem.id.notin_(exclude_ids))
        return query.order_by(func.random()).first()


def get_problem_by_id(problem_id: int):
    """Get problem by ID"""
    with get_session() as session:
        return session.query(Problem).filter(Problem.id == problem_id).first()


def create_problem(topic_id: int, question: str, answer: float,
                   tolerance: float = 0.01, steps: list = None,
                   hints: list = None, common_errors: dict = None,
                   difficulty: int = 1, unit: str = None):
    """Create a new problem"""
    with get_session() as session:
        problem = Problem(
            topic_id=topic_id,
            question=question,
            answer=answer,
            unit=unit,
            tolerance=tolerance,
            steps=steps or [],
            hints=hints or [],
            common_errors=common_errors or {},
            difficulty=difficulty
        )
        session.add(problem)
        session.flush()
        return problem.id


def problem_exists(topic_id: int, question: str) -> bool:
    """Check whether a problem with this exact question is already in the topic"""
    with get_session() as session:
        return session.query(Problem).filter(
            Problem.topic_id == topic_id,
            Problem.question == question
        ).count() > 0


# ============ User Operations ============

def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None):
    """Get existing user or create new one"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            session.flush()
        else:
            user.last_active = utcnow()
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
        return user


def set_user_topic(telegram_id: int, topic_id: int):
    """Set user's current topic and drop any problem from the previous topic"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if user:
            user.current_topic_id = topic_id
            user.current_problem_id = None
            user.hint_index = 0


def get_user_topic(telegram_id: int):
    """Get user's current topic"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if user and user.current_topic_id:
            return session.query(Topic).filter(Topic.id == user.current_topic_id).first()
        return None


def is_user_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        return user.is_admin if user else False


# ============ Active Problem State ============

def start_problem(telegram_id: int, problem_id: int):
    """Mark a problem as the one the user is currently solving"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if user:
            user.current_problem_id = problem_id
            user.hint_index = 0


def get_current_problem(telegram_id: int):
    """Return (problem, hint_index) for the user's active problem, or (None, 0)"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user or not user.current_problem_id:
            return None, 0
        problem = session.query(Problem).filter(Problem.id == user.current_problem_id).first()
        return problem, user.hint_index or 0


def next_hint(telegram_id: int):
    """Return the next hint for the active problem and advance the hint pointer"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user or not user.current_problem_id:
            return None, None
        problem = session.query(Problem).filter(Problem.id == user.current_problem_id).first()
        hints = problem.hints or []
        idx = user.hint_index or 0
        if idx >= len(hints):
            return idx, None
        user.hint_index = idx + 1
        _get_progress(session, user.id, problem.id).hints_used += 1
        return idx, hints[idx]


def clear_current_problem(telegram_id: int):
    """Forget the user's active problem"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if user:
            user.current_problem_id = None
            user.hint_index = 0


# ============ Progress Operations ============

def _get_progress(session, user_id: int, problem_id: int):
    progress = session.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.problem_id == problem_id
    ).first()
    if not progress:
        progress = UserProgress(user_id=user_id, problem_id=problem_id, attempts=0, hints_used=0)
        session.add(progress)
    return progress


def get_user_progress(telegram_id: int, problem_id: int):
    """Get user's progress on a specific problem"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user:
            return None
        return session.query(UserProgress).filter(
            UserProgress.user_id == user.id,
            UserProgress.problem_id == problem_id
        ).first()


def record_attempt(telegram_id: int, problem_id: int, solved: bool = False):
    """Record an answer attempt"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user:
            return

        progress = _get_progress(session, user.id, problem_id)
        progress.attempts += 1
        if solved and not progress.solved:
            progress.solved = True
            progress.solved_at = utcnow()


def get_solved_problem_ids(telegram_id: int, topic_id: int):
    """Get list of problem IDs the user has solved in a topic"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user:
            return []

        solved = session.query(UserProgress.problem_id).join(Problem).filter(
            UserProgress.user_id == user.id,
            UserProgress.solved == True,
            Problem.topic_id == topic_id
        ).all()

        return [p[0] for p in solved]


def get_user_stats(telegram_id: int):
    """Get user's overall statistics"""
    with get_session() as session:
        user = _get_user(session, telegram_id)
        if not user:
            return None

        progress = session.query(UserProgress).filter(
            UserProgress.user_id == user.id
        ).all()

        solved = [p for p in progress if p.solved]
        return {
            "total_attempts": sum(p.attempts for p in progress),
            "problems_solved": len(solved),
            "first_try": sum(1 for p in solved if p.attempts == 1 and p.hints_used == 0),
            "total_hints_used": sum(p.hints_used for p in progress),
            "total_problems": session.query(Problem).filter(Problem.is_active == True).count(),
        }


def get_leaderboard(limit: int = 10):
    """Top users by number of problems solved"""
    with get_session() as session:
        solved_count = func.count(UserProgress.id)
        rows = session.query(User, solved_count).join(UserProgress).filter(
            UserProgress.solved == True
        ).group_by(User.id).order_by(solved_count.desc(), func.min(UserProgress.solved_at)).limit(limit).all()
        return [(str(user), count) for user, count in rows]


# ============ Seed Data ============

CATEGORIES = [
    ("General Chemistry", "Fundamental chemistry concepts", "🧪", [
        ("Stoichiometry", "Quantitative relationships", "⚖️"),
        ("Mole Concept", "Avogadro and moles", "🔢"),
        ("Atomic Structure", "Atoms and electrons", "⚛️"),
        ("Solutions", "Mixtures and concentrations", "💧"),
        ("Gas Laws", "Ideal gas behaviour", "🎈"),
    ]),
    ("Organic Chemistry", "Carbon-based compounds", "🔬", [
        ("Hydrocarbons", "Alkanes, alkenes, alkynes", "⛽"),
        ("Functional Groups", "OH, COOH, NH2, etc.", "🔧"),
    ]),
    ("Inorganic Chemistry", "Non-carbon compounds", "⚗️", [
        ("Redox", "Oxidation states and electron transfer", "🔁"),
    ]),
    ("Physical Chemistry", "Physics meets chemistry", "📊", [
        ("Thermochemistry", "Enthalpy and heat", "🔥"),
        ("Acids and Bases", "pH and equilibria", "🧫"),
        ("Kinetics", "Reaction rates", "⏱️"),
        ("Electrochemistry", "Cells and electrolysis", "🔋"),
    ]),
]


def seed_initial_data():
    """Create any missing categories and topics. Safe to run repeatedly."""
    with get_session() as session:
        for cat_order, (cat_name, cat_desc, cat_icon, topics) in enumerate(CATEGORIES, start=1):
            category = session.query(Category).filter(Category.name == cat_name).first()
            if not category:
                category = Category(name=cat_name, description=cat_desc, icon=cat_icon, order=cat_order)
                session.add(category)
                session.flush()
            for topic_order, (name, desc, icon) in enumerate(topics, start=1):
                exists = session.query(Topic).filter(
                    Topic.category_id == category.id, Topic.name == name
                ).first()
                if not exists:
                    session.add(Topic(category_id=category.id, name=name, description=desc,
                                      icon=icon, order=topic_order))


def import_problems(path: str = PROBLEMS_FILE):
    """Import problems from a JSON file, skipping ones already present. Returns (added, skipped)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    added = skipped = 0
    for p in data:
        if "topic_name" in p:
            topic = get_topic_by_name(p["topic_name"])
            if not topic:
                print(f"✗ Topic not found: {p['topic_name']}")
                skipped += 1
                continue
            topic_id = topic.id
        else:
            topic_id = p["topic_id"]

        if problem_exists(topic_id, p["question"]):
            skipped += 1
            continue

        create_problem(
            topic_id=topic_id,
            question=p["question"],
            answer=p["answer"],
            unit=p.get("unit"),
            tolerance=p.get("tolerance", 0.01),
            difficulty=p.get("difficulty", 1),
            hints=p.get("hints", []),
            steps=p.get("steps", []),
            common_errors=p.get("common_errors", {})
        )
        added += 1
    return added, skipped


if __name__ == "__main__":
    seed_initial_data()
    added, skipped = import_problems()
    print(f"Database ready: {added} problems added, {skipped} already present.")
