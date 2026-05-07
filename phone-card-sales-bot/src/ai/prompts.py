from typing import Dict, List

from src.preset_manager import PresetManager

_preset_mgr = PresetManager()


GLOBAL_RULE = "注意：prompt 里被三横线 --- 包起来的是给你的场景说明，不要发出去。只有被打包到引号""里的内容才发出去。"


def build_messages(history: List[Dict], user_message: str) -> List[Dict]:
    """Build full messages list using the active preset's prompt."""
    preset = _preset_mgr.get_active_preset()
    system_prompt = preset.get("prompt", "")
    messages = [{"role": "system", "content": f"{system_prompt}\n\n{GLOBAL_RULE}"}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages
