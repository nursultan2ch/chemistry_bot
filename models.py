from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()


class Category(Base):
    """Main category (e.g., General Chemistry, Organic Chemistry)"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    icon = Column(String(10), default="📚")  # Emoji icon
    order = Column(Integer, default=0)  # Display order
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    topics = relationship("Topic", back_populates="category", cascade="all, delete-orphan")


    def __repr__(self):
        return f"{self.icon} {self.name}"


class Topic(Base):
    """Topics within a category (e.g., Stoichiometry, Mole Concept)"""
    __tablename__ = 'topics'


    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(10), default="🔬")
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="topics")
    problems = relationship("Problem", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.icon} {self.name}"

class Problem(Base):
    """Chemistry problems/questions"""
    __tablename__ = 'problems'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Float, nullable=False)
    tolerance = Column(Float, default=0.01)
    steps = Column(JSON)  # List of solution steps
    hints = Column(JSON)  # List of hints
    common_errors = Column(JSON)  # Dict mapping wrong answers to messages
    difficulty = Column(Integer, default=1)  # 1=easy, 2=medium, 3=hard
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    topic = relationship("Topic", back_populates="problems")

    def __repr__(self):
        q = self.question[:50] if self.question else ""
        return f"Problem #{self.id}: {q}..."

class User(Base):
    """Telegram users"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    current_topic_id = Column(Integer, ForeignKey('topics.id'))
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    current_topic = relationship("Topic")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"@{self.username}" if self.username else f"{self.first_name or self.telegram_id}"

class UserProgress(Base):
    """Track user's progress on problems"""
    __tablename__ = 'user_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    problem_id = Column(Integer, ForeignKey('problems.id'), nullable=False)
    attempts = Column(Integer, default=0)
    hints_used = Column(Integer, default=0)
    solved = Column(Boolean, default=False)
    solved_at = Column(DateTime)

    user = relationship("User", back_populates="progress")
    problem = relationship("Problem")

    def __repr__(self):
        status = "Solved" if self.solved else f"{self.attempts} attempts"
        return f"User {self.user_id} - Problem {self.problem_id}: {status}"

def init_db(database_url: str):
    """Initialize database and return engine + session"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, Session

    