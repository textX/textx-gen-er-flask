import os
from collections import namedtuple
from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader
from txtools.gen import GenDesc
from txtools.exceptions import TextXToolsException
from textx.lang import get_language
from textx.model import children_of_type, model_root, parent_of_type
from er.lang import get_constraint, is_entity_ref, is_enum_ref,\
    attr_type, meta_name


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

    c = get_constraint(obj, 'dbname')

    if c:
        return c.parameters[0]
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


# Structure used to capture relational meta-data
Column = namedtuple('Column', 'name dbname pk fk fk_target dbtype nullable')
Relationship = namedtuple('Relationship', 'name target_class fk_columns')
ForeignKeyConstraint = namedtuple('ForeignKeyConstraint',
                                  'from_col_names target_table to_col_names')


def ent_elements(ent):
    """
    For the given entity returns all columns and relationships.
    Columns are deduced from ER attributes and * references to this entity
    following rules outlined in Notes.org.
    """

    elements = []

    # Find all referers and add columns and relationships.
    for e in children_of_type(model_root(ent), "Entity"):
        for attr in children_of_type(e, "Attribute"):
            if attr_type(attr) is ent and attr.multiplicity.upper == '*':
                elements.extend(columns_target(attr))

    # Add columns and relationships from the direct attributes
    for attr in children_of_type(ent, "Attribute"):
        # 'Many' attributes will have columns in target entity table.
        if attr.multiplicity.upper != '*':
            elements.extend(columns(attr))
        # elements.extend(rel(attr))

    return elements


def columns(attr):
    """
    Returns columns introduced by the given ER attribute.
    """

    if is_entity_ref(attr):
        tattrs = pk_attrs(attr_type(attr))
        fk = len(tattrs) == 1
    else:
        tattrs = [attr]
        fk = False
    pk = attr.id

    # In case of multiple references to the same Entity we need unique
    # column names. Using counter. TODO.
    # counter = 1
    # referenced_entity_counter = {}
    # if clsname == 'Entity':
    #     if ent.name not in referenced_entity_counter:
    #         referenced_entity_counter[ent.name] = 1
    #     else:
    #         referenced_entity_counter[ent.name] += 1
    #         counter = referenced_entity_counter[ent.name]

    # Columns
    columns = []
    for a in tattrs:
        fk_target = ''
        if fk:
            fk_target = '{}.{}'.format(dbname(attr_type(attr)), dbname(a))
            attr_name = attr.name
            col_name = dbname(attr)
        else:
            attr_name = a.name
            col_name = dbname(a)

        nullable = attr.multiplicity.lower == 0
        columns.append(
            Column(name=attr_name,
                   dbname=col_name,
                   pk=pk,
                   fk=fk,
                   fk_target=fk_target,
                   dbtype=dbtype(a),
                   nullable=nullable))

    return columns


def columns_target(attr):
    """
    Returns columns introduced to other side Entity by attr attribute whose
    multiplicity is *.
    """
    assert attr.multiplicity.upper == '*'
    pent = parent_of_type(attr, "Entity")
    tattrs = pk_attrs(pent)

    # Containment ref. semantics is realized by putting columns in PK.
    pk = attr.ref.containment if attr.ref else False
    nullable = not pk

    # column will have FK constraint if it is single column
    fk = len(tattrs) == 1

    # Columns
    columns = []
    for a in tattrs:
        fk_target = ''
        if fk:
            fk_target = '{}.{}'.format(dbname(pent), dbname(a))
        attr_name = a.name
        col_name = dbname(a)

        columns.append(
            Column(name=attr_name,
                    dbname=col_name,
                    pk=pk,
                    fk=fk,
                    fk_target=fk_target,
                    dbtype=dbtype(a),
                    nullable=nullable))

    return columns


def rel(attr):
    """
    Returns relationship for the given ER attribute.
    """


def rel_target(attr):
    """
    Returns relationship for the other side attribute referencing this attr
    entity.
    """


def pk_attrs(ent):
    """
    Return a list of attributes reachable by recursively following id attributes
    in target entities.
    """
    attrs = []
    for a in ent.attributes:
        if a.id:
            if not is_entity_ref(a):
                attrs.append(a)
            else:
                attrs.extend(pk_attrs(a.type.type))
    return attrs


def dbtype(attr):
    """
    Returns SQLAlchemy type for the given er attribute.
    """
    assert not is_entity_ref(attr)
    tname = attr_type(attr).name
    if is_enum_ref(attr):
        return 'db.Enum({})'.format(attr_type(attr).name)
    else:
        if tname in ['int', 'time', 'date']:
            # Simple types
            return {
                'int': 'db.Integer',
                'time': 'db.DateTime',
                'date': 'db.Date',
            }[tname]
        elif tname in ['string']:
            # Types with precision
            return "{}({})".format({
                'string': 'db.String',
            }[tname], attr.type.precision_x)
        elif tname == 'decimal':
            return 'db.Float({}, asdecimal=True)'.format(attr.type.precision_x)


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
    env.filters['ent_elements'] = ent_elements

    return env.get_template(template_path).render(**context)


# This object is registered in setup.py under entry point textx_gen
gendesc = GenDesc(name="er_flask", lang="er",
                  desc='flask generator for er language',
                  genconf=genconf_model,
                  render=render,
                  param_names=PARAM_NAMES)
