import os
from flask import Flask
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.secret_key = os.urandom(24)
db = SQLAlchemy(app)


@app.cli.command()
def initdb():
    """Initializes the database."""
    db.create_all()
    print('Initialized the database.')


@app.route('/')
def index():
    return '<a href="admin/">Click me to go to admin!</a>'


{% for entity in entities %}
class {{entity.name}}(db.Model):
    __tablename__ = '{{entity|dbname}}'

    {% for attr in entity|all("Attribute") %}
    {{attr.name}} = db.Column('{{attr|dbname}}')
    {%- endfor %}

{% endfor %}

{% for enum in enums %}
Enum: {{enum.name}}
{% endfor %}
