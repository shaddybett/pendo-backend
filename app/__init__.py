from flask import Flask
from app.extensions.db import db
from flask_migrate import Migrate

migrate = Migrate()

def create_app():
    app = Flask(__name__)

    app.config.from_object("app.config.config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    return app