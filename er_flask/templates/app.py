import os
from flask import Flask

app = Flask(__name__)
app.secret_key = os.urandom(24)

import model
import admin


@app.cli.command()
def initdb():
    """Initializes the database."""
    model.db.create_all()
    print('Initialized the database.')


@app.route('/')
def index():
    return '<a href="admin/">Click me to go to admin!</a>'
