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

from flask_mail import Mail, Message
import uuid

from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)

# Eerst SECRET_KEY instellen, anders is die None bij serializer
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mijngeheim123')

# Mailconfiguratie
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='infoquovadis@gmail.com',
    MAIL_PASSWORD='asym udsz lyqt paiw'
)

mail = Mail(app)

# Nu pas serializer aanmaken met geldige SECRET_KEY
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# CORS
CORS(app, resources={r"/api/*": {"origins": "https://clearbuypicks.onrender.com"}})

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


class VisiblePasswordField(PasswordField):
    widget = TextInput()


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


@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Veiligheid: geen info of mail bestaat
        return jsonify({"message": "If this email exists, a reset link will be sent"}), 200

    reset_token = serializer.dumps(email, salt='password-reset-salt')

    reset_link = f"https://jouwdomein.com/reset-password?token={reset_token}"  # Pas aan naar frontend URL

    msg = Message("Password Reset Request",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.body = f"Klik op deze link om je wachtwoord te resetten: {reset_link}"
    mail.send(msg)

    return jsonify({"message": "If this email exists, a reset link will be sent"}), 200


@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')

    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400

    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # Token 1 uur geldig
    except Exception:
        return jsonify({"error": "Invalid or expired token"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password has been reset successfully"}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
