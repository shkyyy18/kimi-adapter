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


def test_pdf_base64_without_pypdf():
    """When pypdf is unavailable the adapter should degrade gracefully."""
    import sys

    real_modules = sys.modules.copy()
    sys.modules["pypdf"] = None  # simulate missing import
    try:
        payload = {
            "messages": [
                {
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": "JVBERi0xLjQKJdPr6eEKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooSGVsbG8sIFBERikgVGoKRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0hlbHZldGljYQovRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZwo+PgplbmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAwMDAwMjA3IDAwMDAwIG4gCjAwMDAwMDAzMDEgMDAwMDAgbiAKdHJhaWxlcgo8PAovU2l6ZSA2Ci9Sb290IDEgMCBSCj4+CnN0YXJ0eHJlZgozODEKJSVFT0Y=",
                            },
                        }
                    ]
                }
            ]
        }
        n = convert_documents(payload)
        assert n == 1
        text = payload["messages"][0]["content"][0]["text"]
        assert text.startswith("\n\n<附件内容(PDF已提取为文本)")
        assert "pypdf is not installed" in text or "Hello, PDF" in text
    finally:
        sys.modules.clear()
        sys.modules.update(real_modules)


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
