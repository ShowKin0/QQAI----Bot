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


@pytest.mark.asyncio
async def test_should_respond_trigger_keyword():
    handler = MessageHandler.__new__(MessageHandler)
    settings = {"trigger_keywords": ["卡", "流量"]}
    assert handler._should_respond({}, "有流量卡吗", settings) is True
    assert handler._should_respond({}, "你好呀", settings) is False


@pytest.mark.asyncio
async def test_should_respond_at_bot():
    handler = MessageHandler.__new__(MessageHandler)
    settings = {"trigger_keywords": ["卡"], "bot_qq": "12345"}
    assert handler._should_respond({"raw_message": "[CQ:at,qq=12345] 你好"}, "", settings) is True
