import os
import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from {{project_name.lower()}} import app

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)


{% for enum in enums %}
class {{enum.name}}(enum.Enum):
    {%- for lit in enum.literals %}
    {{lit.name}} = "{{lit.code}}"
    {%- endfor %}

{% endfor %}

{%- for entity in entities %}
class {{entity.name}}(db.Model):
    __tablename__ = '{{entity|dbname}}'
    {% set elements, fk_constraints = entity|ent_elements -%}
    {% for elem in elements %}
    {%- if elem.__class__.__name__ == 'Column' %}
    {{elem.name}} = db.Column('{{elem.dbname}}', {{elem.dbtype}}
                              {%- if elem.fk %}, db.ForeignKey('{{elem.fk_target}}'){% endif %}
                              {%- if elem.pk %}, primary_key=True{% endif %}
                              {%- if elem.nullable %}, nullable=True{% endif %})
    {%- else %}
    {{elem.name}} = relationship('{{elem.target_ent.name}}',
                                 {%- if elem.target_ent == entity %} remote_side=[{{entity|pk_attrs|map(attribute='name')|join(", ")}}],{% endif -%}
                                 {% if elem.fk_columns %} foreign_keys=[{{- elem.fk_columns|map(attribute='name')|join(', ')}}]{% endif %}, backref='{{elem.backref}}')
    {%- endif %}
    {%- endfor %}

    {%- if fk_constraints %}

    __table_args__ = (
        {%- for fkc in fk_constraints %}
        db.ForeignKeyConstraint([{{fkc.fk_columns|map(attribute='dbname')|map('quote')|join(", ")}}],
                                [{{fkc.fk_columns|map(attribute='fk_target')|map('quote')|join(", ")}}],
                                name='{{fkc.name}}'),
        {%- endfor %}
    )
    {%- endif -%}

    {%- if entity|display %}

    def __str__(self):
        {%- set self_list = entity|display|format_list("self.{}") %}
        if {{self_list|join(" and ")}}:
        {%- set sp = joiner(' ') %}
            return "{% for i in self_list %}{{sp()}}{}{% endfor %}".format({{entity|display|format_list("self.{}")|join(', ')}})
        else:
            return super({{entity.name}}, self).__str__()
    {%- endif %}

{% endfor %}

