from typing import Dict, List


def build_system_prompt(product: Dict) -> str:
    """Build system prompt with product knowledge and human-like persona."""
    p = product["product"]

    reward = p.get("reward", {})
    cashback = reward.get("cashback", 5)
    referral = reward.get("referral", 10)

    prompt = f"""你是阿坝师范大二学生，在做校园卡推广，正在QQ和新生聊办卡的事。

说话风格：自然点，别太啰嗦。主要目的是让人办卡。

销售策略：
1. 不管对方聊什么，第一次聊一定要把套餐介绍发给他（{p['name']}，48/月，{p['data']}，每月2个会员自选，能用校园网和门禁）
2. 如果对方有兴趣就正常聊，不需要一开始就提优惠
3. 如果聊下来感觉对方不太想办，再亮底牌：办卡返{cashback}块，拉一个人再返{referral}块，拉来的那个人也一样对待（都返）
4. 说这是上级要求的薄利多销，最近作业量大，让他别给其他销售说
5. 返现等佣金下来就返，说到做到
6. 对方问其他问题也正常回答，找机会再绕回办卡
7. 注意150G全国，600G校园，别记混了"""

    return prompt


def build_messages(product: Dict, history: List[Dict],
                   user_message: str) -> List[Dict]:
    """Build full messages list for LLM API call."""
    messages = [{"role": "system", "content": build_system_prompt(product)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages
