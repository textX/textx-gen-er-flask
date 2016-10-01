import os
from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader
from txtools.gen import GenDesc
from txtools.exceptions import TextXToolsException
from textx.lang import get_language
from textx.model import all_of_type
from er.lang import get_constraint


PARAM_NAMES = ('flask_admin', 'composite_keys')


def genconf_model():
    """
    Returns genconf model for 'er_flask' generator and 'er'
    language.
    """
    gc_meta = get_language("genconf")
    curr_dir = os.path.dirname(__file__)
    gc_model = gc_meta.model_from_file(
        os.path.join(curr_dir, 'er_flask.genconf'))

    # Check parameters
    for p in gc_model.params:
        if p.name not in PARAM_NAMES:
            raise TextXToolsException('Undefined generator parameter "{}".'
                                      .format(p.name))

    return gc_model


def dbname(obj):

    p = get_constraint(obj, 'dbname')

    if p:
        return p[0]
    else:
        # Construct default db name
        tname = obj.name[0].upper()
        for letter in obj.name[1:]:
            if letter.isupper():
                tname += "_"
            tname += letter.upper()
        return tname


def all(obj, type_name):
    lang = get_language("er")
    return all_of_type(lang, obj, type_name)


def render(template_path, context, root_path=None):
    """
    Returns rendered template. By default search for template at the given
    root path. If not found search is continued in the generator templates
    folder.

    Args:
        template_path (str): Relative path to the template inside the root_path.
        context (dict)
        root_path (str): The root where templates should be searched first.
    """

    # By default jinja2 is used but this can be changed by the user.
    env = Environment(loader=ChoiceLoader([
        FileSystemLoader(root_path),
        PackageLoader('er_flask', 'templates')
    ]))

    env.filters['dbname'] = dbname
    env.filters['all'] = all

    return env.get_template(template_path).render(**context)


# This object is registered in setup.py under entry point textx_gen
gendesc = GenDesc(name="er_flask", lang="er",
                  desc='flask generator for er language',
                  genconf=genconf_model,
                  render=render,
                  param_names=PARAM_NAMES)
