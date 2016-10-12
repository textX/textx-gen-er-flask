from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin
from {{project_name.lower()}} import app
import model

# Flask Admin views
admin = Admin(app, name='{{project_name}}', template_mode='{{flask_admin_template_mode}}')

{% for entity in  entities %}
{%- set elements, fk_constraints = entity|ent_elements -%}
{%- set category = entity|category -%}
class {{entity.name}}View(ModelView):
    column_display_pk = True
    form_columns = (
        {%- for elem in elements %}
        {%- if not elem.fk %}
        '{{elem.name}}'{% if not loop.last %},{% endif %}
        {%- endif %}
        {%- endfor %}
    )
admin.add_view({{entity.name}}View(model.{{entity.name}}, model.db.session{% if category %}, category='{{category}}'{% endif %}))
{% endfor %}
