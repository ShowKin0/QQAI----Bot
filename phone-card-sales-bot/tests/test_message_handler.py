import pytest
from src.handler.message import MessageHandler


def test_extract_text_from_array_message():
    handler = MessageHandler.__new__(MessageHandler)
    msg = [
        {"type": "text", "data": {"text": "你好"}},
        {"type": "text", "data": {"text": "，有卡吗"}},
    ]
    assert handler._extract_text(msg) == "你好，有卡吗"


def test_extract_text_ignores_non_text():
    handler = MessageHandler.__new__(MessageHandler)
    msg = [
        {"type": "at", "data": {"qq": "123"}},
        {"type": "text", "data": {"text": "hi"}},
    ]
    assert handler._extract_text(msg) == "hi"


def test_extract_text_empty():
    handler = MessageHandler.__new__(MessageHandler)
    assert handler._extract_text([]) == ""


def test_split_message_below_max():
    result = MessageHandler._split_message("你好", 80)
    assert result == ["你好"]


def test_split_message_at_punctuation():
    text = "流量卡很划算的。一个月48块钱。750G流量。还有其他福利。"
    result = MessageHandler._split_message(text, 15)
    assert len(result) >= 3
    for s in result:
        assert len(s.strip()) <= 16


def test_split_message_long_no_punct():
    text = "a" * 100
    result = MessageHandler._split_message(text, 30)
    assert all(len(s) <= 30 for s in result)


@pytest.mark.asyncio
async def test_should_respond_trigger_keyword():
    handler = MessageHandler.__new__(MessageHandler)
    handler.config = {"bot": {"trigger_keywords": ["卡", "流量"]}}
    assert handler._should_respond({}, "有流量卡吗") is True
    assert handler._should_respond({}, "你好呀") is False


@pytest.mark.asyncio
async def test_should_respond_at_bot():
    handler = MessageHandler.__new__(MessageHandler)
    handler.config = {"bot": {"trigger_keywords": ["卡"], "qq": "12345"}}
    assert handler._should_respond({"raw_message": "[CQ:at,qq=12345] 你好"}, "") is True
