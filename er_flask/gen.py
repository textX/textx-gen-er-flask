import os
from collections import namedtuple
from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader
from txtools.gen import GenDesc
from txtools.exceptions import ValidationError
from textx.lang import get_language
from textx.model import children_of_type, model_root, parent_of_type
from er.lang import get_constraint, is_entity_ref, is_enum_ref, attr_type


def genconf_model():
    """
    Returns genconf model for 'er_flask' generator and 'er'
    language.
    """
    gc_meta = get_language("genconf")
    curr_dir = os.path.dirname(__file__)
    gc_model = gc_meta.model_from_file(
        os.path.join(curr_dir, 'er_flask.genconf'))

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


# Structure used to capture relational meta-data
# Column:
#   ent - parent Entity
#   from_attr - introduced based on attribute
#   pk - is part of primary key
#   fk - is a single-column foreign key
#   fk_target - Table.column spec. for the target. Used if fk.
#   dbtype - sqlalchemy db type
#   nullable - is nullable
Column = namedtuple('Column',
                    'name dbname ent from_attr pk fk fk_target dbtype nullable')
# Relationship:
#   name - the name of the class attribute
#   target_ent - target Entity object from the model
#   fk_columns - a list of columns used to implement this relationship
#   backref - the name of the other end class attribute
Relationship = namedtuple('Relationship',
                          'name target_ent fk_columns backref')
# ForeignKeyConstraint:
#   fk_columns - a list of columns used to implement this constraint
#   targe_ent - target Entity object from the model
ForeignKeyConstraint = namedtuple('ForeignKeyConstraint',
                                  'fk_columns target_ent')


def ent_elements(ent):
    """
    For the given entity returns all columns and relationships.
    Columns are deduced from ER attributes and * references to this entity
    following rules outlined in Notes.org.
    """

    elements = []

    # Find all referrers and add columns and relationships.
    print("Processing table ", ent.name)
    for e in children_of_type(model_root(ent), "Entity"):
        if e is ent:
            continue
        print("\tAnalysing entity", e.name)
        for attr in children_of_type(e, "Attribute"):
            if attr_type(attr) is ent:
                print("\t\tAttribute", attr.name)
                print("\t\t\t{}".format([a.name for a in columns(ent, attr)]))
                for c in columns(ent, attr):
                    append_column(elements, c, ent)
                elements.append(rel(ent, attr))

    # Add columns and relationships from the direct attributes
    for attr in children_of_type(ent, "Attribute"):
        for c in columns(ent, attr):
            append_column(elements, c, ent)
        if is_entity_ref(attr):
            elements.append(rel(ent, attr))

    # Foreign key constraint exists if there is relationship over more
    # than one column.
    # fk_constraints = []
    # for e in elements:
    #     if type(e) is Relationship:
    #         if len(e.fk_columns) > 1:
    #             fk_constraints.append(
    #                 ForeignKeyConstraint(
    #                     fk_columns=e.fk_columns,
    #                     target_ent=e.target_ent))
    # elements.extend(fk_constraints)

    return elements


def append_column(l, column, ent):
    """
    Appends column to the given list l. If the column already exists do some
    sanity check and merge.
    """
    for idx, c in enumerate(l):
        if type(c) is Column:
            assert c.ent is column.ent
            assert c.name != column.name, "{} already introduced in {} by {}"\
                .format(c.name, ent.name, c.ent.name)
            if c.name == column.name:
                assert c.dbname == column.dbname
                assert c.dbtype == column.dbtype
                if c.fk and column.fk:
                    assert c.fk_target == column.fk_target
                l[idx] = Column(name=c.name,
                                dbname=c.dbname,
                                ent=c.ent,
                                pk=c.pk or column.pk,
                                fk=c.fk or column.fk,
                                fk_target=c.fk_target or column.fk_target,
                                dbtype=c.dbtype,
                                nullable=c.nullable and column.nullable)
                break
    else:
        l.append(column)


def columns(ent,  attr):
    """
    Returns columns introduced on the given Entity by the given ER attribute.
    """

    pent = parent_of_type(attr, "Entity")

    assert pent is ent or (is_entity_ref(attr) and attr_type(attr) is ent)

    other_side = pent is not ent

    if is_entity_ref(attr):
        if not other_side:
            # 'Many' attributes will have columns in target entity table.
            if attr.multiplicity.upper == '*':
                return []
            target_ent = attr_type(attr)
        else:
            # Other side attr with non-many mult. doesn't create any columns.
            if attr.multiplicity.upper == 1:
                return []
            target_ent = pent
        tattrs = pk_attrs(target_ent)
        fk = len(tattrs) == 1
    else:
        tattrs = [attr]
        fk = False
    pk = attr.id

    columns = []
    for a in tattrs:
        if fk:
            col_name = attr.name + '_id'
        else:
            col_name = a.name
        db_col_name = dbname(a)
        if is_entity_ref(attr):
            fk_target = '{}.{}'.format(dbname(target_ent), db_col_name)
        else:
            fk_target = ''

        nullable = attr.multiplicity.lower == 0
        columns.append(
            Column(name=col_name,
                   dbname=db_col_name,
                   ent=ent,
                   from_attr=attr,
                   pk=pk,
                   fk=fk,
                   fk_target=fk_target,
                   dbtype=dbtype(a),
                   nullable=nullable))

    return columns


def back_ref(attr):
    """
    Returns the name of other side of bidirectional relationship.
    """
    if attr.ref and attr.ref.bidir:
        return attr.ref.other_side
    else:
        return parent_of_type(attr, "Entity").name.lower()


def rel(ent, attr):
    """
    Returns relationship for the given ER attribute.
    """
    pent = parent_of_type(attr, "Entity")
    assert pent is ent or attr_type(attr) is ent

    if pent is ent:
        return Relationship(name=attr.name,
                            target_ent=attr_type(attr),
                            fk_columns=columns(ent, attr),
                            backref=back_ref(attr))
    else:
        return Relationship(name=back_ref(attr),
                            target_ent=pent,
                            fk_columns=columns(ent, attr),
                            backref=attr.name)


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
                attrs.extend(pk_attrs(attr_type(a)))
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


def validate(model):
    """
    Generator specific validation of ER models.
    Throws ValidationError if there is an error in the model.
    """

    for ent in children_of_type(model, "Entity"):
        without_dbname = set()
        for attr in children_of_type(ent, "Attribute"):
            if is_entity_ref(attr) and get_constraint(attr, "dbname") is None:
                target_entity_name = attr_type(attr).name
                if target_entity_name in without_dbname:
                    raise ValidationError(
                        "While validating '{}.{}'. Multiple references to the "
                        "same target Entity '{}' without 'dbname' definition."
                        .format(ent.name, attr.name, target_entity_name))
                without_dbname.add(target_entity_name)


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
                  validate=validate)
