from flask import Flask
from app.extensions.db import db
from app.utils.firebase import *
from app.routes.auth_routes import auth_bp
from flask_migrate import Migrate
from app.models import User, UserPhoto, Swipe, Match, Message, Block

migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config.from_object("app.config.config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)

    return app
