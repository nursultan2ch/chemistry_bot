import os
import random
from datetime import datetime, timezone
from contextlib import contextmanager
from dotenv import load_dotenv

from models import (
    init_db, Category, Topic, Problem, User, UserProgress
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/chemistry_bot")

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


def get_random_problem(topic_id: int, exclude_ids: list = None):
    """Get a random problem from a topic, optionally excluding already solved"""
    with get_session() as session:
        query = session.query(Problem).filter(
            Problem.topic_id == topic_id,
            Problem.is_active == True
        )
        if exclude_ids:
            query = query.filter(Problem.id.notin_(exclude_ids))

        problems = query.all()
        if not problems:
            return None
        return random.choice(problems)


def get_problem_by_id(problem_id: int):
    """Get problem by ID"""
    with get_session() as session:
        return session.query(Problem).filter(Problem.id == problem_id).first()


def create_problem(topic_id: int, question: str, answer: float,
                   tolerance: float = 0.01, steps: list = None,
                   hints: list = None, common_errors: dict = None,
                   difficulty: int = 1):
    """Create a new problem"""
    with get_session() as session:
        problem = Problem(
            topic_id=topic_id,
            question=question,
            answer=answer,
            tolerance=tolerance,
            steps=steps or [],
            hints=hints or [],
            common_errors=common_errors or {},
            difficulty=difficulty
        )
        session.add(problem)
        session.flush()
        return problem.id


# ============ User Operations ============

def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None):
    """Get existing user or create new one"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            session.flush()
        else:
            user.last_active = datetime.now(timezone.utc)
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
        return user


def set_user_topic(telegram_id: int, topic_id: int):
    """Set user's current topic"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.current_topic_id = topic_id


def get_user_topic(telegram_id: int):
    """Get user's current topic"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.current_topic_id:
            return session.query(Topic).filter(Topic.id == user.current_topic_id).first()
        return None


def is_user_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return user.is_admin if user else False


# ============ Progress Operations ============

def get_user_progress(telegram_id: int, problem_id: int):
    """Get user's progress on a specific problem"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        return session.query(UserProgress).filter(
            UserProgress.user_id == user.id,
            UserProgress.problem_id == problem_id
        ).first()


def record_attempt(telegram_id: int, problem_id: int, solved: bool = False, hint_used: bool = False):
    """Record a problem attempt"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return

        progress = session.query(UserProgress).filter(
            UserProgress.user_id == user.id,
            UserProgress.problem_id == problem_id
        ).first()

        if not progress:
            progress = UserProgress(user_id=user.id, problem_id=problem_id, attempts=0, hints_used=0)
            session.add(progress)

        progress.attempts += 1
        if hint_used:
            progress.hints_used += 1
        if solved:
            progress.solved = True
            progress.solved_at = datetime.now(timezone.utc)


def get_solved_problem_ids(telegram_id: int, topic_id: int):
    """Get list of problem IDs the user has solved in a topic"""
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
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
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None

        progress = session.query(UserProgress).filter(
            UserProgress.user_id == user.id
        ).all()

        return {
            "total_attempts": sum(p.attempts for p in progress),
            "problems_solved": sum(1 for p in progress if p.solved),
            "total_hints_used": sum(p.hints_used for p in progress)
        }


# ============ Seed Data ============

def seed_initial_data():
    """Seed database with initial categories and topics"""
    with get_session() as session:
        # Check if data already exists
        if session.query(Category).count() > 0:
            print("Database already has data, skipping seed.")
            return

        # Create categories
        general = Category(name="General Chemistry", description="Fundamental chemistry concepts", icon="🧪", order=1)
        organic = Category(name="Organic Chemistry", description="Carbon-based compounds", icon="🔬", order=2)
        inorganic = Category(name="Inorganic Chemistry", description="Non-carbon compounds", icon="⚗️", order=3)
        physical = Category(name="Physical Chemistry", description="Physics meets chemistry", icon="📊", order=4)
        biochem = Category(name="Biochemistry", description="Chemistry of living systems", icon="🧬", order=5)

        session.add_all([general, organic, inorganic, physical, biochem])
        session.flush()

        # Create topics for General Chemistry
        topics_general = [
            Topic(category_id=general.id, name="Stoichiometry", description="Quantitative relationships", icon="⚖️", order=1),
            Topic(category_id=general.id, name="Mole Concept", description="Avogadro and moles", icon="🔢", order=2),
            Topic(category_id=general.id, name="Atomic Structure", description="Atoms and electrons", icon="⚛️", order=3),
            Topic(category_id=general.id, name="Chemical Bonding", description="How atoms bond", icon="🔗", order=4),
            Topic(category_id=general.id, name="Solutions", description="Mixtures and concentrations", icon="🧪", order=5),
        ]
        

        # Create topics for Organic Chemistry
        topics_organic = [
            Topic(category_id=organic.id, name="Hydrocarbons", description="Alkanes, alkenes, alkynes", icon="⛽", order=1),
            Topic(category_id=organic.id, name="Functional Groups", description="OH, COOH, NH2, etc.", icon="🔧", order=2),
            Topic(category_id=organic.id, name="Reactions", description="Organic reaction mechanisms", icon="💥", order=3),
        ]

        session.add_all(topics_general + topics_organic)
        session.flush()

        print("Database seeded with categories and topics!")
        print("Use the admin panel (python admin.py) to add problems.")


if __name__ == "__main__":
    seed_initial_data()
