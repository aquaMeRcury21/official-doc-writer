"""Shared fixtures for all tests."""

import os
import sys
import tempfile

import pytest

# Ensure the project root is on sys.path so utils can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def sample_text():
    return '这是一段测试文本。用于测试文档解析功能。'
