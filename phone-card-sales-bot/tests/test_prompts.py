from src.ai.prompts import build_system_prompt, build_messages

SAMPLE_PRODUCT = {
    "product": {
        "name": "校园畅享卡",
        "price": 48,
        "data": "750GB/月（150GB全国通用 + 600GB校园流量）",
        "membership": {
            "count": 2,
            "description": "每月可自选两款会员（视频/音乐平台）",
            "platforms": ["腾讯视频", "爱奇艺", "网易云音乐"],
        },
        "features": ["可使用校园网", "自带宿舍门禁功能"],
        "target": "阿坝师范学院新生",
        "faq": [
            {"q": "可以开热点吗？", "a": "可以"},
            {"q": "需要学生证吗？", "a": "不需要"},
        ],
    }
}


def test_build_system_prompt_contains_product_info():
    prompt = build_system_prompt(SAMPLE_PRODUCT)
    assert "校园畅享卡" in prompt
    assert "48" in prompt
    assert "750GB" in prompt
    assert "150GB" in prompt
    assert "门禁" in prompt
    assert "校园网" in prompt


def test_build_system_prompt_contains_faq():
    prompt = build_system_prompt(SAMPLE_PRODUCT)
    assert "开热点" in prompt
    assert "学生证" in prompt


def test_build_system_prompt_has_human_tone_instructions():
    prompt = build_system_prompt(SAMPLE_PRODUCT)
    assert "学长" in prompt or "学姐" in prompt
    assert "阿坝师范学院" in prompt
    assert "QQ" in prompt


def test_build_messages_structure():
    history = [{"role": "assistant", "content": "你好呀"}]
    messages = build_messages(SAMPLE_PRODUCT, history, "有流量卡吗")
    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "你好呀"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "有流量卡吗"
