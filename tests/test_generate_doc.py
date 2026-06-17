"""Tests for generate_doc.py — template engine (_resolve, _fill_template)."""

import json

from utils.generate_doc import _fill_template, _resolve


class TestResolve:
    def test_simple_key(self):
        assert _resolve('name', {'name': '张三'}) == '张三'

    def test_nested_key(self):
        assert _resolve('a.b', {'a': {'b': 'value'}}) == 'value'

    def test_missing_key_returns_empty(self):
        assert _resolve('missing', {'a': 1}) == ''

    def test_partial_missing_returns_empty(self):
        assert _resolve('a.b.c', {'a': {}}) == ''

    def test_list_index(self):
        assert _resolve('items.0', {'items': ['a', 'b']}) == 'a'

    def test_list_index_out_of_range(self):
        assert _resolve('items.5', {'items': ['a']}) == ''

    def test_dict_value_returns_json(self):
        val = _resolve('nested', {'nested': {'x': 1}})
        parsed = json.loads(val)
        assert parsed == {'x': 1}

    def test_list_value_returns_json(self):
        val = _resolve('items', {'items': [1, 2]})
        parsed = json.loads(val)
        assert parsed == [1, 2]

    def test_none_returns_empty(self):
        assert _resolve('key', {'key': None}) == ''


class TestFillTemplate:
    def test_simple_variable(self):
        result = _fill_template('{{name}}您好', {'fields': {'name': '张三'}})
        assert result == '张三您好'

    def test_multiple_variables(self):
        result = _fill_template(
            '{{greeting}}，{{name}}',
            {'fields': {'name': '张三', 'greeting': '你好'}},
        )
        assert result == '你好，张三'

    def test_missing_variable_renders_empty(self):
        result = _fill_template('{{missing}}', {'fields': {}})
        assert result == ''

    def test_list_block(self):
        data = {
            'fields': {},
            'lists': {
                'items': [
                    {'name': '任务一', 'status': '完成'},
                    {'name': '任务二', 'status': '进行中'},
                ],
            },
        }
        tpl = '{{#items}}{{name}}：{{status}}\n{{/items}}'
        result = _fill_template(tpl, data)
        assert '任务一：完成' in result
        assert '任务二：进行中' in result

    def test_empty_list_renders_nothing(self):
        data = {'fields': {}, 'lists': {'items': []}}
        result = _fill_template('{{#items}}{{name}}{{/items}}', data)
        assert result == ''

    def test_non_list_variable_does_not_loop(self):
        data = {'fields': {}, 'lists': {'items': 'not_a_list'}}
        result = _fill_template('{{#items}}x{{/items}}', data)
        assert result == ''

    def test_variable_from_data_root_title(self):
        result = _fill_template('标题：{{title}}', {
            'title': '关于XX的通知',
            'fields': {},
        })
        assert '关于XX的通知' in result

    def test_variable_from_data_root_doc_type(self):
        result = _fill_template('文种：{{docType}}', {
            'docType': '通知',
            'fields': {},
        })
        assert '文种：通知' in result
