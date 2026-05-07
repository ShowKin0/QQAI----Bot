from src.ai.prompts import build_messages
from src.preset_manager import PresetManager


def test_build_messages_structure():
    history = [{"role": "assistant", "content": "你好呀"}]
    messages = build_messages(history, "有流量卡吗")
    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] != ""  # prompt loaded from preset
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "你好呀"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "有流量卡吗"


def test_build_messages_loads_from_active_preset():
    mgr = PresetManager()
    preset = mgr.get_active_preset()
    assert preset.get("prompt", "") != ""
    messages = build_messages([], "hello")
    # system content should include preset prompt + global rule
    assert preset["prompt"] in messages[0]["content"]
    assert "三横线" in messages[0]["content"]
