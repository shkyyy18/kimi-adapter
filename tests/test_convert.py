import json

import pytest

from kimi_adapter.adapter import convert_documents


def test_convert_simple_document():
    payload = {
        "model": "kimi-for-coding",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请分析这个文件"},
                    {
                        "type": "document",
                        "source": {"type": "text", "data": "print('hello world')"},
                    },
                ],
            }
        ],
    }
    n = convert_documents(payload)
    assert n == 1
    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "text"
    assert "print('hello world')" in content[1]["text"]


def test_convert_nested_documents():
    payload = {
        "messages": [
            {
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "text", "data": "a"},
                    },
                    {
                        "type": "document",
                        "source": {"type": "text", "data": "b"},
                    },
                ]
            }
        ]
    }
    n = convert_documents(payload)
    assert n == 2


def test_ignores_non_text_documents():
    payload = {
        "messages": [
            {
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "data": "deadbeef"},
                    }
                ]
            }
        ]
    }
    n = convert_documents(payload)
    assert n == 0
    assert payload["messages"][0]["content"][0]["type"] == "document"


def test_no_documents():
    payload = {"messages": [{"content": [{"type": "text", "text": "hello"}]}]}
    n = convert_documents(payload)
    assert n == 0


def test_json_roundtrip_stability():
    """Ensure converted payload is still valid JSON after serialization."""
    payload = {
        "messages": [
            {
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "text", "data": "{"},
                    }
                ]
            }
        ]
    }
    convert_documents(payload)
    json.dumps(payload)
