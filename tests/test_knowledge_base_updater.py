"""Tests for knowledge_base_updater.py — classify, collect, process."""


from utils.knowledge_base_updater import (
    classify,
    collect_files,
    process_all,
)


class TestClassify:
    def test_empty_text_returns_archive(self):
        layer, sub = classify('')
        assert layer == 'archive'

    def test_notice_keyword_classifies_notice(self):
        text = '现将有关事项通知如下：各单位请遵照执行。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '通知'

    def test_report_keyword_classifies_report(self):
        text = '现将有关情况报告如下，特此报告。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '报告'

    def test_request_keyword_classifies_request(self):
        text = '现就有关问题请示如下，妥否，请批示。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '请示'

    def test_speech_keyword_classifies_speech(self):
        text = '同志们：在此，我代表市委向大家表示热烈欢迎。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '讲话稿'

    def test_summary_keyword_classifies_summary(self):
        text = '一年来，在市委的坚强领导下，主要做法及成效如下。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '总结'

    def test_meeting_minutes_keyword(self):
        text = '会议纪要如下，会议指出，要抓好落实。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '纪要'

    def test_briefing_keyword(self):
        text = '工作简报：本期工作动态如下。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '简报'

    def test_letter_keyword(self):
        text = '致函：关于商请协助的函。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '函'

    def test_scheme_keyword(self):
        text = '本工作方案明确了总体要求和重点任务。'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '方案'

    def test_global_keyword_classifies_global(self):
        text = '习近平在中共中央政治局会议上强调，要深化改革开放。'
        layer, sub = classify(text)
        assert layer == 'global'
        assert sub == ''

    def test_tie_prefers_higher_ratio(self):
        text = '特此通知。现将有关情况报告如下'
        layer, sub = classify(text)
        assert layer == 'category'
        assert sub == '报告'


class TestCollectFiles:
    def test_collects_supported_extensions(self, tmp_path):
        (tmp_path / 'test.txt').write_text('hello', encoding='utf-8')
        (tmp_path / 'test.docx').write_text('dummy', encoding='utf-8')
        (tmp_path / 'test.pdf').write_text('dummy', encoding='utf-8')
        (tmp_path / 'ignored.exe').write_text('dummy', encoding='utf-8')
        (tmp_path / '.hidden').write_text('dummy', encoding='utf-8')
        files = collect_files(tmp_path)
        names = [f.name for f in files]
        assert 'test.txt' in names
        assert 'test.docx' in names
        assert 'test.pdf' in names
        assert 'ignored.exe' not in names

    def test_empty_dir_returns_empty(self, tmp_path):
        assert collect_files(tmp_path) == []


class TestProcessAll:
    def test_process_txt_file(self, tmp_path):
        src = tmp_path / 'inbox'
        src.mkdir()
        (src / 'notice.txt').write_text(
            '现将有关事项通知如下，请遵照执行。', encoding='utf-8')
        stats = process_all(str(src))
        assert stats['processed'] >= 1
        assert not (src / 'notice.txt').exists()

    def test_nonexistent_dir_returns_error(self):
        stats = process_all('/nonexistent/path')
        assert 'error' in stats

    def test_empty_inbox_returns_warning(self, tmp_path):
        src = tmp_path / 'empty_inbox'
        src.mkdir()
        stats = process_all(str(src))
        assert 'warning' in stats
