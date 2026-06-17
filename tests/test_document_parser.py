"""Tests for document_parser.py — text chunking, heading detection, hash."""

from utils.document_parser import chunk_text, file_hash, is_heading_line


class TestHeadingDetection:
    def test_level1_heading(self):
        assert is_heading_line('一、指导思想') is True
        assert is_heading_line('二、基本原则') is True
        assert is_heading_line('十、组织领导') is True

    def test_level2_heading(self):
        assert is_heading_line('（一）加强领导') is True
        assert is_heading_line('（二）落实责任') is True

    def test_not_heading(self):
        assert is_heading_line('这是一段普通正文') is False
        assert is_heading_line('') is False
        assert is_heading_line('一') is False


class TestChunkText:
    def test_empty_text(self):
        chunks = chunk_text('', 'test.txt')
        assert chunks == []

    def test_single_paragraph(self):
        text = ('这是一段测试文本，用于验证分块功能是否正常。'
                '一共需要超过三十个字符才能满足最小分块要求。')
        chunks = chunk_text(text, 'test.txt')
        assert len(chunks) == 1
        assert chunks[0]['source'] == 'test.txt'

    def test_heading_splits_chunks(self):
        text = ('一、背景\n'
                '这是背景内容的详细介绍部分。需要超过三十个字符才能满足最小分块的门槛要求。'
                '这里补充更多内容来确保达到三十个字符的门槛。\n'
                '二、目标\n'
                '这是目标内容的详细介绍部分。也需要超过三十个字符才能满足最小分块的门槛要求。'
                '这里补充更多内容来确保第二个片段也能达到三十个字符的门槛。')
        chunks = chunk_text(text, 'test.txt')
        assert len(chunks) >= 2

    def test_empty_lines_skipped(self):
        chunks = chunk_text('\n\n\n', 'test.txt')
        assert chunks == []

    def test_file_hash_consistency(self, tmp_path):
        f = tmp_path / 'test.txt'
        f.write_text('hello world', encoding='utf-8')
        h1 = file_hash(str(f))
        h2 = file_hash(str(f))
        assert h1 == h2

    def test_file_hash_differs(self, tmp_path):
        f1 = tmp_path / 'a.txt'
        f2 = tmp_path / 'b.txt'
        f1.write_text('hello', encoding='utf-8')
        f2.write_text('world', encoding='utf-8')
        assert file_hash(str(f1)) != file_hash(str(f2))
