import os
from flask import Flask
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import enum

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

{% for enum in enums %}
class {{enum.name}}(enum.Enum):
    {%- for lit in enum.literals %}
    {{lit.name}} = "{{lit.code}}"
    {%- endfor %}

{% endfor %}

{% for entity in entities %}
class {{entity.name}}(db.Model):
    __tablename__ = '{{entity|dbname}}'

    {% for elem in entity|ent_elements %}
    {%- if elem.__class__.__name__ == 'Column' %}
    {{elem.name}} = db.Column('{{elem.dbname}}', {{elem.dbtype}}
                              {%- if elem.fk %}, db.ForeignKey('{{elem.fk_target}}'){% endif %}
                              {%- if elem.pk %}, primary_key=True{% endif %}
                              {%- if elem.nullable %}, nullable=True{% endif %})
    {%- else %}
    {{elem.name}} = relationship('{{elem.target_class}}'{% if elem.fk_columns %}, foreign_keys=[
        {{- elem.fk_columns|map(attribute='name')|join(', ')}}]{% endif %}, back_populates='{{elem.backref}}')
    {%- endif %}
    {%- endfor %}

{% endfor %}


# Flask Admin views
admin = Admin(app, name='{{project_name}}', template_mode='bootstrap3')

{% for entity in  entities %}
class {{entity.name}}View(ModelView):
    column_display_pk = True
    form_columns = (
        {%- for elem in entity|ent_elements %}
        '{{elem.name}}'{% if not loop.last %}, {% endif %}
        {%- endfor %}
    )
admin.add_view({{entity.name}}View({{entity.name}}, db.session))
{% endfor %}

