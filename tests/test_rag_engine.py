"""Tests for rag_engine.py — search, index, stats."""


from utils.rag_engine import LAYER_DIRS, RAGEngine


class TestRAGEngineInit:
    def test_init_creates_empty_cache(self):
        engine = RAGEngine()
        assert engine._cache == {}

    def test_stats_returns_dict(self):
        engine = RAGEngine()
        stats = engine.stats()
        assert 'global' in stats
        assert 'category' in stats
        assert 'archive' in stats
        assert stats['embedding_mode'] == 'tfidf-cache'


class TestRAGEngineSearch:
    def _make_test_layer(self, tmp_path):
        """Create a temp layer with a sample .txt file and register it."""
        layer_dir = tmp_path / 'test-layer'
        layer_dir.mkdir()
        sample_file = layer_dir / 'sample.txt'
        sample_file.write_text(
            '这是一篇关于理论学习的重要文章，内容涵盖意识形态工作的方方面面。'
            '各级党员干部都要认真研读并深入领会精神实质。\n\n'
            '理论学习是党员干部的必修课，必须常抓不懈久久为功。'
            '要坚持读原著学原文悟原理，做到学思用贯通知信行统一。\n\n'
            '要深入学习习近平新时代中国特色社会主义思想，这是当前和今后一个时期的重要政治任务。'
            '必须全面系统学、深入思考学、联系实际学。',
            encoding='utf-8',
        )
        return str(layer_dir)

    def test_search_finds_relevant_content(self, tmp_path):
        engine = RAGEngine()
        layer_dir = self._make_test_layer(tmp_path)
        layer_name = 'test_layer_find'
        LAYER_DIRS[layer_name] = layer_dir
        try:
            info = engine._build_layer_index(layer_name, force=True)
            assert info['chunks'] > 0, f'Index built 0 chunks: {info}'
            results = engine.search('理论学习', layer=layer_name, top_k=3)
            assert len(results) > 0
            assert results[0]['score'] > 0
        finally:
            del LAYER_DIRS[layer_name]

    def test_search_empty_query_returns_list(self, tmp_path):
        engine = RAGEngine()
        layer_dir = self._make_test_layer(tmp_path)
        layer_name = 'test_layer_empty'
        LAYER_DIRS[layer_name] = layer_dir
        try:
            engine._build_layer_index(layer_name, force=True)
            results = engine.search('', layer=layer_name, top_k=3)
            assert isinstance(results, list)
        finally:
            del LAYER_DIRS[layer_name]

    def test_search_as_context_returns_string(self, tmp_path):
        engine = RAGEngine()
        layer_dir = self._make_test_layer(tmp_path)
        layer_name = 'test_layer_ctx'
        LAYER_DIRS[layer_name] = layer_dir
        try:
            info = engine._build_layer_index(layer_name, force=True)
            assert info['chunks'] > 0, f'Index built 0 chunks: {info}'
            ctx = engine.search_as_context('理论学习', layer=layer_name, top_k=2)
            assert isinstance(ctx, str)
            assert len(ctx) > 0
        finally:
            del LAYER_DIRS[layer_name]

    def test_layer_index_builds_chunks(self, tmp_path):
        engine = RAGEngine()
        layer_dir = self._make_test_layer(tmp_path)
        layer_name = 'test_layer_chunks'
        LAYER_DIRS[layer_name] = layer_dir
        try:
            info = engine._build_layer_index(layer_name, force=True)
            assert info['files_processed'] >= 1
            assert info['chunks'] > 0
        finally:
            del LAYER_DIRS[layer_name]
