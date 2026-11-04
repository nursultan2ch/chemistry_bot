import hmac
import os
import sys
from flask import Flask, Response, redirect, request
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.orm import scoped_session
from dotenv import load_dotenv

from datetime import timedelta

from models import init_db, utcnow, Category, Topic, Problem, User, UserProgress

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/chemistry_bot")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")

if not ADMIN_PASSWORD or not SECRET_KEY:
    sys.exit("ADMIN_PASSWORD and SECRET_KEY must be set (see .env.example)")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Initialize database; one session per request instead of one shared by every request
engine, Session = init_db(DATABASE_URL)
session = scoped_session(Session)


# ============ Authentication ============

def _credentials_ok(auth):
    return (
        auth is not None
        and hmac.compare_digest(auth.username or "", ADMIN_USERNAME)
        and hmac.compare_digest(auth.password or "", ADMIN_PASSWORD)
    )


@app.before_request
def require_basic_auth():
    if request.path == '/healthz':
        return None
    if not _credentials_ok(request.authorization):
        return Response('Login required', 401, {'WWW-Authenticate': 'Basic realm="Chemistry Bot Admin"'})
    return None


# ============ Custom Admin Views ============

class SecureModelView(ModelView):
    """Base view; every request is already authenticated by require_basic_auth"""

    column_display_pk = True
    can_export = True
    can_view_details = True
    page_size = 50


class CategoryView(SecureModelView):
    """Admin view for categories"""
    column_list = ['id', 'icon', 'name', 'description', 'order', 'is_active', 'created_at']
    column_searchable_list = ['name', 'description']
    column_filters = ['is_active']
    column_editable_list = ['name', 'icon', 'order', 'is_active']
    form_excluded_columns = ['topics', 'created_at']

    column_labels = {
        'icon': 'Icon (Emoji)',
        'order': 'Display Order'
    }


class TopicView(SecureModelView):
    """Admin view for topics"""
    column_list = ['id', 'category', 'icon', 'name', 'description', 'order', 'is_active']
    column_searchable_list = ['name', 'description']
    column_filters = ['category', 'is_active']
    column_editable_list = ['name', 'icon', 'order', 'is_active']
    form_excluded_columns = ['problems', 'created_at']

    column_labels = {
        'category': 'Category',
        'icon': 'Icon (Emoji)',
        'order': 'Display Order'
    }


class ProblemView(SecureModelView):
    """Admin view for problems"""
    column_list = ['id', 'topic', 'question', 'answer', 'unit', 'difficulty', 'is_active']
    column_searchable_list = ['question']
    column_filters = ['topic', 'difficulty', 'is_active']
    column_editable_list = ['difficulty', 'is_active']
    form_excluded_columns = ['created_at']

    column_labels = {
        'topic': 'Topic',
        'unit': 'Answer Unit',
        'tolerance': 'Answer Tolerance (±)',
        'steps': 'Solution Steps (JSON list)',
        'hints': 'Hints (JSON list)',
        'common_errors': 'Common Errors (JSON dict)'
    }

    form_widget_args = {
        'question': {'rows': 4},
        'steps': {'rows': 6},
        'hints': {'rows': 4},
        'common_errors': {'rows': 4}
    }

    column_descriptions = {
        'unit': 'Shown to students, e.g. "g" or "kJ/mol"',
        'tolerance': 'Acceptable error margin for answers',
        'steps': 'Enter as JSON list: ["Step 1", "Step 2"]',
        'hints': 'Enter as JSON list: ["Hint 1", "Hint 2"]',
        'common_errors': 'Enter as JSON dict: {"1.0": "Wrong molar mass"}'
    }


class UserView(SecureModelView):
    """Admin view for users"""
    column_list = ['id', 'telegram_id', 'username', 'first_name', 'is_admin', 'created_at', 'last_active']
    column_searchable_list = ['username', 'first_name']
    column_filters = ['is_admin']
    column_editable_list = ['is_admin']
    can_create = False
    can_delete = False
    form_excluded_columns = ['progress', 'current_topic', 'current_problem', 'hint_index']


class UserProgressView(SecureModelView):
    """Admin view for user progress"""
    column_list = ['id', 'user', 'problem', 'attempts', 'hints_used', 'solved', 'solved_at']
    column_filters = ['solved']
    can_create = False
    can_edit = False


class DashboardView(AdminIndexView):
    """Custom dashboard"""
    @expose('/')
    def index(self):
        stats = {
            'categories': session.query(Category).count(),
            'topics': session.query(Topic).count(),
            'problems': session.query(Problem).count(),
            'users': session.query(User).count(),
            'active_week': session.query(User).filter(User.last_active >= utcnow() - timedelta(days=7)).count(),
            'solved': session.query(UserProgress).filter(UserProgress.solved == True).count()
        }
        return self.render('admin/dashboard.html', stats=stats)


# ============ Create Admin ============

admin = Admin(
    app,
    name='Chemistry Bot Admin',
    template_mode='bootstrap4',
    index_view=DashboardView()
)

# Add views
admin.add_view(CategoryView(Category, session, name='Categories', category='Content'))
admin.add_view(TopicView(Topic, session, name='Topics', category='Content'))
admin.add_view(ProblemView(Problem, session, name='Problems', category='Content'))
admin.add_view(UserView(User, session, name='Users', category='Users'))
admin.add_view(UserProgressView(UserProgress, session, name='Progress', category='Users'))


# ============ Routes ============

@app.route('/')
def index():
    return redirect('/admin')


@app.route('/healthz')
def healthz():
    return 'ok'


@app.teardown_appcontext
def remove_session(exc=None):
    session.remove()


if __name__ == '__main__':
    port = int(os.getenv("ADMIN_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
