from unittest.mock import Mock
from honyaku.cli import identify_entry
from honyaku.cli import is_translatable
from honyaku.cli import is_translated


def test_identify_entry():
    entry1 = Mock()
    entry1.msgid = 'To be translated'
    entry2 = Mock()
    entry2.msgid = 'Some other text'
    assert identify_entry(entry1) != identify_entry(entry2)


def test_is_translatable():
    entry = Mock()
    entry.msgid = ''
    assert not is_translatable(entry)
    entry.msgid = '   '
    assert not is_translatable(entry)
    entry.msgid = 'Translatable'
    assert is_translatable(entry)


def test_is_translated():
    entry = Mock()
    entry.msgstr = ''
    assert not is_translated(entry)
    entry.msgstr = '   '
    assert not is_translated(entry)
    entry.msgstr = 'Translated text'
    assert is_translated(entry)
