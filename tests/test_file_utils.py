"""Tests for file_utils.py — archive_working_files."""


from utils.file_utils import archive_working_files


class TestArchiveWorkingFiles:
    def test_moves_files_to_target(self, tmp_path, monkeypatch):
        src = tmp_path / 'workspace'
        src.mkdir()
        (src / 'ref.txt').write_text('reference', encoding='utf-8')
        (src / 'notes.md').write_text('notes', encoding='utf-8')
        monkeypatch.setattr('utils.file_utils.WORKING_DIR', str(src))
        target = tmp_path / 'target'
        target.mkdir()
        moved = archive_working_files(str(target))
        assert len(moved) >= 2
        assert (target / 'ref.txt').exists()
        assert (target / 'notes.md').exists()

    def test_nonexistent_source_returns_empty_list(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / 'nonexistent'
        monkeypatch.setattr('utils.file_utils.WORKING_DIR', str(nonexistent))
        target = tmp_path / 'target'
        target.mkdir()
        moved = archive_working_files(str(target))
        assert moved == []
