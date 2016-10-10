import pytest
from textx.lang import get_language
from er_flask.gen import columns


def test_columns_with_dbcols():
    model_str = """
    model test
    constraint dbcols applies to attr
    entity First {
        a: Second: dbcols(trt, vrt)
    }

    entity Second {
        #b: Third
    }

    entity Third {

        #c: int
        #d: string(10)
    }

    """

    mm = get_language('er')
    model = mm.model_from_str(model_str)

    ent = model.elements[0]
    attr = ent.attributes[0]
    cols = columns(ent, attr)
    assert len(cols) == 2
    assert cols[0].name == 'trt'
    assert cols[1].name == 'vrt'


def test_columns_without_dbcols():
    model_str = """
    model test
    entity First {
        a: Second
    }

    entity Second {
        #b: Third
    }

    entity Third {

        #c: int
        #d: string(10)
    }

    """

    mm = get_language('er')
    model = mm.model_from_str(model_str)

    ent = model.elements[0]
    attr = ent.attributes[0]
    cols = columns(ent, attr)
    assert len(cols) == 2
    assert cols[0].name == 'c'
    assert cols[1].name == 'd'

