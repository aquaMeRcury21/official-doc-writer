"""
RAG 向量检索引擎 —— TF-IDF 缓存矩阵（三层统一方案）

三层架构：
    global-knowledge/    单位通用政策、年度要点、长效文件（书记讲话范文等）
    category-knowledge/  按文种分类（工作总结、通知、请示…）
    archive/             已生成文稿归档（查重、文风比对）

每层独立缓存 TF-IDF 向量化器 + 稀疏矩阵 + 元数据，
搜索时加载缓存直接计算余弦相似度，无需 ChromaDB。

用法：
    from utils.rag_engine import RAGEngine
    rag = RAGEngine()
    rag.index_all()                    # 首次全量索引（预计算所有层）
    results = rag.search("意识形态", layer='global', top_k=5)
    ctx = rag.search_as_context("理论学习", layer='global')
"""

import json
import logging
import os
import pickle
import re
from typing import Optional

from scipy.sparse import load_npz, save_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .document_parser import read_document
from .settings import KNOWLEDGE_BASE

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(str(KNOWLEDGE_BASE), 'tfidf_cache')

LAYER_DIRS = {
    'global':   os.path.join(KNOWLEDGE_BASE, 'global-knowledge'),
    'category': os.path.join(KNOWLEDGE_BASE, 'category-knowledge'),
    'archive':  os.path.join(KNOWLEDGE_BASE, 'archive'),
}

CHUNK_CHARS = 500        # 段落超长时二次切分字符数
MAX_FEATURES = 4096      # TF-IDF 最大特征数


class RAGEngine:
    """TF-IDF 缓存矩阵检索引擎，三层统一方案。"""

    def __init__(self):
        self._cache = {}  # layer -> {vec, matrix, metadata}

    # ── 缓存路径 ────────────────────────────────

    def _vec_path(self, layer: str) -> str:
        return os.path.join(CACHE_DIR, f'{layer}_vectorizer.pkl')

    def _mat_path(self, layer: str) -> str:
        return os.path.join(CACHE_DIR, f'{layer}_matrix.npz')

    def _meta_path(self, layer: str) -> str:
        return os.path.join(CACHE_DIR, f'{layer}_metadata.json')

    def _index_exists(self, layer: str) -> bool:
        return (os.path.isfile(self._vec_path(layer))
                and os.path.isfile(self._mat_path(layer))
                and os.path.isfile(self._meta_path(layer)))

    # ── 加载缓存（惰性） ────────────────────────

    def _load_layer(self, layer: str):
        if layer in self._cache:
            return
        if not self._index_exists(layer):
            self._cache[layer] = None
            return
        with open(self._vec_path(layer), 'rb') as f:
            vec = pickle.load(f)
        matrix = load_npz(self._mat_path(layer))
        with open(self._meta_path(layer), 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        self._cache[layer] = {'vec': vec, 'matrix': matrix, 'metadata': metadata}

    # ── 构建单层索引 ────────────────────────────

    def _build_layer_index(self, layer: str, force: bool = False) -> dict:
        dir_path = LAYER_DIRS[layer]
        if not os.path.isdir(dir_path):
            return {'files_processed': 0, 'chunks': 0}

        if self._index_exists(layer) and not force:
            self._load_layer(layer)
            cached = self._cache.get(layer)
            n = cached['matrix'].shape[0] if cached else 0
            return {'files_processed': 0, 'chunks': n, 'cached': True}

        texts = []
        metadata = []
        file_count = 0

        for root, _, files in os.walk(dir_path):
            for fname in sorted(files):
                if not fname.endswith('.txt'):
                    continue
                fpath = os.path.join(root, fname)
                content = read_document(fpath)
                if not content:
                    continue
                file_count += 1
                paragraphs = re.split(r'\n\s*\n', content.strip())
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                    if len(para) <= CHUNK_CHARS * 2:
                        if len(para) >= 30:
                            texts.append(para)
                            metadata.append(
                                {'source': fpath, 'fname': fname,
                                 'text': para, 'heading': ''}
                            )
                    else:
                        for i in range(0, len(para), CHUNK_CHARS):
                            chunk = para[i:i + CHUNK_CHARS].strip()
                            if len(chunk) >= 30:
                                texts.append(chunk)
                                metadata.append(
                                    {'source': fpath, 'fname': fname,
                                     'text': chunk, 'heading': ''}
                                )

        if not texts:
            return {'files_processed': file_count, 'chunks': 0}

        vec = TfidfVectorizer(max_features=MAX_FEATURES,
                              ngram_range=(1, 2), analyzer='char_wb')
        matrix = vec.fit_transform(texts)
        logger.info('%s TF-IDF: %d 片段, %d 特征', layer, len(texts), matrix.shape[1])

        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(self._vec_path(layer), 'wb') as f:
            pickle.dump(vec, f)
        save_npz(self._mat_path(layer), matrix)
        with open(self._meta_path(layer), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False)

        self._cache[layer] = {'vec': vec, 'matrix': matrix, 'metadata': metadata}
        return {'files_processed': file_count, 'chunks': len(texts)}

    # ── 搜索 ────────────────────────────────────

    def search(self, query: str, layer: Optional[str] = None,
               top_k: int = 5, min_score: float = 0.1) -> list[dict]:
        layers = [layer] if layer else list(LAYER_DIRS.keys())
        all_results = []

        for lyr in layers:
            self._load_layer(lyr)
            cached = self._cache.get(lyr)
            if cached is None:
                continue

            vec = cached['vec']
            matrix = cached['matrix']
            metadata = cached['metadata']

            q_vec = vec.transform([query])
            scores = cosine_similarity(q_vec, matrix)[0]
            top_indices = scores.argsort()[::-1]

            for idx in top_indices:
                score = float(scores[idx])
                if score < min_score:
                    break
                if idx >= len(metadata):
                    continue
                meta = metadata[idx]
                all_results.append({
                    'text': meta.get('text', ''),
                    'source': meta['source'],
                    'heading': meta.get('heading', ''),
                    'layer': lyr,
                    'score': round(score, 4),
                })
                if len(all_results) >= top_k:
                    break

        all_results.sort(key=lambda x: -x['score'])
        return all_results[:top_k]

    def search_as_context(self, query: str, layer: Optional[str] = None,
                           top_k: int = 5, max_chars: int = 3000) -> str:
        results = self.search(query, layer=layer, top_k=top_k)
        parts = []
        total = 0
        for r in results:
            snippet = r['text'][:200]
            src = f"[来源: {r['source']} | 层: {r['layer']} | 相关度: {r['score']}]\n{snippet}"
            parts.append(src)
            total += len(src)
            if total > max_chars:
                break
        return '\n\n'.join(parts)

    # ── 全量索引 ────────────────────────────────

    def index_all(self, force: bool = False) -> dict:
        results = {}
        for layer, dir_path in LAYER_DIRS.items():
            if not os.path.isdir(dir_path):
                logger.warning('目录不存在 %s', dir_path)
                results[layer] = {'files_processed': 0, 'chunks': 0}
                continue
            logger.info('构建 %s 索引 → %s', layer, dir_path)
            results[layer] = self._build_layer_index(layer, force=force)
        return results

    def add_file(self, filepath: str, layer: str) -> int:
        """添加新文件后重建对应层的索引"""
        if layer in self._cache:
            del self._cache[layer]
        result = self._build_layer_index(layer, force=True)
        return result['chunks']

    # ── 统计 ────────────────────────────────────

    def stats(self) -> dict:
        result = {}
        for layer in LAYER_DIRS:
            self._load_layer(layer)
            cached = self._cache.get(layer)
            n = cached['matrix'].shape[0] if cached else 0
            result[layer] = {'chunks': n, 'dir': LAYER_DIRS[layer]}
        result['embedding_mode'] = 'tfidf-cache'
        return result


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('用法: python rag_engine.py index|search|stats')
        sys.exit(1)

    rag = RAGEngine()
    cmd = sys.argv[1]

    if cmd == 'index':
        force = '--force' in sys.argv
        print(f'索引中 (force={force})...')
        results = rag.index_all(force=force)
        for layer, r in results.items():
            print(f'  {layer}: {r["chunks"]} chunks, {r["files_processed"]} files')
        print('索引完成。统计:', json.dumps(rag.stats(), ensure_ascii=False))

    elif cmd == 'search':
        query = sys.argv[2] if len(sys.argv) > 2 else input('查询: ')
        layer = sys.argv[3] if len(sys.argv) > 3 else None
        results = rag.search(query, layer=layer, top_k=5)
        for i, r in enumerate(results, 1):
            print(f'\n--- #{i} [{r["layer"]}] score={r["score"]} '
                  f'src={r["source"]} ---')

    elif cmd == 'stats':
        print(json.dumps(rag.stats(), ensure_ascii=False, indent=2))

    else:
        print(f'未知命令: {cmd}')
