from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from wtforms import PasswordField, StringField, Form
from wtforms.validators import DataRequired, Email
from wtforms.widgets import TextInput

from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://clearbuypicks.onrender.com"}})
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mijngeheim123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

# Maak een zichtbaar wachtwoordveld (geen sterretjes)
class VisiblePasswordField(PasswordField):
    widget = TextInput()

# Custom WTForms formulier voor User admin
class UserForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = VisiblePasswordField('Password', validators=[DataRequired()])

class UserAdmin(ModelView):
    form = UserForm
    form_excluded_columns = ('password_hash', 'created_at')

    def on_model_change(self, form, model, is_created):
        if form.password.data:
            model.set_password(form.password.data)

    column_list = ('email', 'created_at')

admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')
admin.add_view(UserAdmin(User, db.session))


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password or not name:
        return jsonify({"error": "Please provide name, email and password"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    new_user = User(email=email, name=name)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/')
def home():
    return "API is running"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
