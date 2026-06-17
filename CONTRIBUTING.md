# Contributing to official-doc-writer

## Development Setup

```bash
git clone https://github.com/your-username/official-doc-writer.git
cd official-doc-writer
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your DeepSeek API key
```

## Code Style

- Follow PEP 8. Run `ruff check .` before committing.
- Line length: 100 characters.
- Quotes: single quotes for Python strings.
- All new code must include tests.

## Pull Request Process

1. Create a feature branch from `main`.
2. Write or update tests for your changes.
3. Run `ruff check .` and `pytest` — both must pass.
4. Keep PRs focused: one feature or fix per PR.
5. Write a clear PR description explaining what and why.

## Commit Messages

Use conventional commits:

```
feat: add support for X
fix: correct Y in the RAG engine
docs: update README installation steps
refactor: merge extract_word_to_txt and com_extract
test: add tests for cost_tracker
```

## Project Conventions

- Never commit real government documents or API keys.
- Never modify files under `knowledge-base/global-knowledge/` or `knowledge-base/category-knowledge/`.
- All placeholder strings like `[单位名称]` belong in `utils/settings.py`, not in source code.
- Run `python -c "from utils.rag_engine import RAGEngine; RAGEngine().index_all()"` after changes to knowledge base utils.

## Reporting Issues

Use GitHub Issues. Include:
- Python version
- Full traceback for bugs
- Steps to reproduce
- Expected vs actual behavior
