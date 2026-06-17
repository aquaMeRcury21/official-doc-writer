"""Tests for document_generator.py — punctuation normalization."""

from utils.document_generator import _PH_RE, _normalize_punctuation


class TestPunctuationNormalization:
    def test_ascii_to_fullwidth(self):
        result = _normalize_punctuation('你好,世界.')
        assert '\uff0c' in result  # fullwidth comma
        assert '\u3002' in result  # fullwidth period

    def test_double_quotes_conversion(self):
        result = _normalize_punctuation('他说"你好"')
        assert '\u201c' in result  # left double quote
        assert '\u201d' in result  # right double quote

    def test_single_quotes_conversion(self):
        result = _normalize_punctuation("他说'你好'")
        assert '\u2018' in result  # left single quote
        assert '\u2019' in result  # right single quote

    def test_numeric_preserved(self):
        result = _normalize_punctuation('价格是3.5元')
        assert '3.5' in result

    def test_url_preserved(self):
        result = _normalize_punctuation('请访问https://example.com')
        assert 'https://example.com' in result

    def test_email_preserved(self):
        result = _normalize_punctuation('联系test@example.com')
        assert 'test@example.com' in result

    def test_empty_input(self):
        assert _normalize_punctuation('') == ''


class TestPlaceholderRegex:
    def test_matches_placeholder(self):
        assert _PH_RE.fullmatch('[待补充]') is not None
        assert _PH_RE.fullmatch('[具体数据]') is not None

    def test_non_match(self):
        assert _PH_RE.fullmatch('正文内容') is None
