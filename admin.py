import os
from flask import Flask, redirect, url_for, request
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_basicauth import BasicAuth
from dotenv import load_dotenv

from models import init_db, Category, Topic, Problem, User, UserProgress

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/chemistry_bot")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
app.config['BASIC_AUTH_USERNAME'] = ADMIN_USERNAME
app.config['BASIC_AUTH_PASSWORD'] = ADMIN_PASSWORD
app.config['BASIC_AUTH_FORCE'] = True

basic_auth = BasicAuth(app)

# Initialize database
engine, Session = init_db(DATABASE_URL)
session = Session()


# ============ Custom Admin Views ============

class SecureModelView(ModelView):
    """Base view with authentication"""
    def is_accessible(self):
        return True  # BasicAuth handles this at app level

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
    column_list = ['id', 'topic', 'question', 'answer', 'difficulty', 'is_active']
    column_searchable_list = ['question']
    column_filters = ['topic', 'difficulty', 'is_active']
    column_editable_list = ['difficulty', 'is_active']
    form_excluded_columns = ['created_at']

    column_labels = {
        'topic': 'Topic',
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
    form_excluded_columns = ['progress', 'current_topic']


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


# ============ Custom Templates ============

@app.route('/')
def index():
    return redirect('/admin')


# Create custom dashboard template
import os
templates_dir = os.path.join(os.path.dirname(__file__), 'templates', 'admin')
os.makedirs(templates_dir, exist_ok=True)

dashboard_template = '''
{% extends 'admin/master.html' %}
{% block body %}
<div class="container-fluid">
    <h1>Dashboard</h1>
    <div class="row mt-4">
        <div class="col-md-4 mb-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <h5 class="card-title">Categories</h5>
                    <h2>{{ stats.categories }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h5 class="card-title">Topics</h5>
                    <h2>{{ stats.topics }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <h5 class="card-title">Problems</h5>
                    <h2>{{ stats.problems }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card bg-warning">
                <div class="card-body">
                    <h5 class="card-title">Users</h5>
                    <h2>{{ stats.users }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card bg-secondary text-white">
                <div class="card-body">
                    <h5 class="card-title">Problems Solved</h5>
                    <h2>{{ stats.solved }}</h2>
                </div>
            </div>
        </div>
    </div>
    <hr>
    <h3>Quick Links</h3>
    <ul>
        <li><a href="/admin/category/new/">Add New Category</a></li>
        <li><a href="/admin/topic/new/">Add New Topic</a></li>
        <li><a href="/admin/problem/new/">Add New Problem</a></li>
    </ul>
</div>
{% endblock %}
'''

with open(os.path.join(templates_dir, 'dashboard.html'), 'w') as f:
    f.write(dashboard_template)


if __name__ == '__main__':
    port = int(os.getenv("ADMIN_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
