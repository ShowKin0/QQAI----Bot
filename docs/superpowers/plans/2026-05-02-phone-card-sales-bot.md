# Phone Card Sales QQ Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based QQ bot that connects via NapCatQQ (reverse WebSocket) and uses LLM API to act as a natural "senior student" selling campus phone cards to freshmen.

**Architecture:** Independent Python service connects to NapCatQQ via reverse WebSocket (OneBot v11 protocol). Incoming messages are routed through a Session Manager (per-user context), then to AI Service (LLM API call with product knowledge in system prompt). Reply is sent back through NapCatQQ, with optional long-message splitting for human-like feel. Order handling is a stub for future integration.

**Tech Stack:** Python 3.10+, `websockets` (NapCatQQ comm), `httpx` (LLM API), `pyyaml` (config), `python-dotenv` (env vars), `pytest` (tests).

---

### Task 1: Project scaffold + config files

**Files:**
- Create: `phone-card-sales-bot/requirements.txt`
- Create: `phone-card-sales-bot/.env.example`
- Create: `phone-card-sales-bot/config/settings.yaml`
- Create: `phone-card-sales-bot/config/product.yaml`
- Create: `phone-card-sales-bot/src/__init__.py`
- Create: `phone-card-sales-bot/src/adapter/__init__.py`
- Create: `phone-card-sales-bot/src/ai/__init__.py`
- Create: `phone-card-sales-bot/src/session/__init__.py`
- Create: `phone-card-sales-bot/src/handler/__init__.py`
- Create: `phone-card-sales-bot/src/order/__init__.py`
- Create: `phone-card-sales-bot/tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
websockets>=12.0
httpx>=0.27.0
pyyaml>=6.0
python-dotenv>=1.0.0
pytest>=8.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 2: Create `.env.example`**

```bash
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com/v1
```

- [ ] **Step 3: Create `config/settings.yaml`**

```yaml
server:
  host: "0.0.0.0"
  port: 8765
  ws_path: "/onebot/v11/ws"

llm:
  api_key: "${LLM_API_KEY}"
  base_url: "${LLM_BASE_URL}"
  model: "deepseek-chat"
  temperature: 0.7
  max_tokens: 1024

session:
  max_rounds: 10
  expire_minutes: 30

bot:
  name: "校园助手"
  qq: ""
  trigger_keywords: ["卡", "流量", "套餐", "电话卡"]

human_like:
  enable_message_split: true
  split_delay: 0.8
  max_segment_length: 80
```

- [ ] **Step 4: Create `config/product.yaml`**

```yaml
product:
  name: "校园畅享卡"
  price: 48
  data: "750GB/月（150GB全国通用 + 600GB校园流量）"
  membership:
    count: 2
    description: "每月可自选两款会员（视频/音乐平台）"
    platforms: ["腾讯视频", "爱奇艺", "网易云音乐", "QQ音乐", "B站"]
  features:
    - "可使用校园网"
    - "自带宿舍门禁功能"
    - "150GB全国通用流量"
    - "600GB校园区域流量（教学楼、宿舍、食堂均可使用）"
  target: "阿坝师范学院新生"
  faq:
    - q: "可以开热点吗？"
      a: "可以，流量不限制"
    - q: "需要学生证吗？"
      a: "新生凭录取通知书即可办理"
    - q: "毕业后还能用吗？"
      a: "可以继续使用，套餐不变"
    - q: "750G都是通用流量吗？"
      a: "150G是全国通用，剩下600G在校园范围内用，教学楼宿舍食堂都有信号，平时在学校完全够用"
```

- [ ] **Step 5: Create all `__init__.py` files** (all empty files in `src/` subdirectories and `tests/`)

Run:
```bash
touch phone-card-sales-bot/src/__init__.py
touch phone-card-sales-bot/src/adapter/__init__.py
touch phone-card-sales-bot/src/ai/__init__.py
touch phone-card-sales-bot/src/session/__init__.py
touch phone-card-sales-bot/src/handler/__init__.py
touch phone-card-sales-bot/src/order/__init__.py
touch phone-card-sales-bot/tests/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add phone-card-sales-bot/
git commit -m "feat: project scaffold with config files and directory structure"
```

---

### Task 2: Config loader

**Files:**
- Create: `phone-card-sales-bot/src/config_loader.py`
- Create: `phone-card-sales-bot/tests/test_config_loader.py`

- [ ] **Step 1: Write the test**

```python
import os
import tempfile
from pathlib import Path
import yaml

from src.config_loader import load_config, _resolve_env_vars

def test_load_config_loads_settings_and_product():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        config_dir = base / "config"
        config_dir.mkdir()
        
        (config_dir / "settings.yaml").write_text("""
server:
  host: "0.0.0.0"
  port: 8765
llm:
  api_key: "${TEST_KEY}"
  model: "test-model"
""")
        (config_dir / "product.yaml").write_text("""
product:
  name: "测试卡"
  price: 48
""")
        os.environ["TEST_KEY"] = "sk-test123"
        
        result = load_config(base)
        assert result["settings"]["server"]["host"] == "0.0.0.0"
        assert result["settings"]["server"]["port"] == 8765
        assert result["settings"]["llm"]["api_key"] == "sk-test123"
        assert result["settings"]["llm"]["model"] == "test-model"
        assert result["product"]["product"]["name"] == "测试卡"

def test_resolve_env_vars_replaces_placeholder():
    obj = {"key": "${MY_VAR}", "nested": {"inner": "${OTHER}"}}
    os.environ["MY_VAR"] = "value1"
    os.environ["OTHER"] = "value2"
    _resolve_env_vars(obj)
    assert obj["key"] == "value1"
    assert obj["nested"]["inner"] == "value2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_config_loader.py -v`
Expected: FAIL with ImportError/ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

```python
import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(base_dir: str | Path = ".") -> Dict[str, Any]:
    """Load settings.yaml and product.yaml, resolving env var placeholders."""
    base = Path(base_dir)
    settings_path = base / "config" / "settings.yaml"
    product_path = base / "config" / "product.yaml"

    with open(settings_path, encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    _resolve_env_vars(settings)

    with open(product_path, encoding="utf-8") as f:
        product = yaml.safe_load(f)

    return {"settings": settings, "product": product}


def _resolve_env_vars(obj: Any) -> None:
    """Recursively resolve ${VAR_NAME} placeholders in config values."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                obj[k] = os.environ.get(env_key, "")
            else:
                _resolve_env_vars(v)
    elif isinstance(obj, list):
        for item in obj:
            _resolve_env_vars(item)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_config_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add phone-card-sales-bot/src/config_loader.py phone-card-sales-bot/tests/test_config_loader.py
git commit -m "feat: add config loader with env var resolution"
```

---

### Task 3: Session Manager

**Files:**
- Create: `phone-card-sales-bot/src/session/manager.py`
- Create: `phone-card-sales-bot/tests/test_session_manager.py`

- [ ] **Step 1: Write the test**

```python
import time
from src.session.manager import SessionManager

def test_get_or_create_creates_new_session():
    mgr = SessionManager()
    session = mgr.get_or_create("user_1")
    assert session.user_id == "user_1"
    assert session.messages == []

def test_get_or_create_returns_existing_session():
    mgr = SessionManager()
    s1 = mgr.get_or_create("user_1")
    s2 = mgr.get_or_create("user_1")
    assert s1 is s2

def test_add_message_appends_and_trims():
    mgr = SessionManager(max_rounds=2)
    mgr.add_message("user_1", "user", "hi")
    mgr.add_message("user_1", "assistant", "hello")
    mgr.add_message("user_1", "user", "how r u")
    mgr.add_message("user_1", "assistant", "good")
    mgr.add_message("user_1", "user", "third round")
    # max_rounds=2 => max 4 messages. After 5th msg, should keep last 4.
    history = mgr.get_history("user_1")
    assert len(history) == 4
    assert history[0]["content"] == "how r u"

def test_is_first_interaction():
    mgr = SessionManager()
    assert mgr.is_first_interaction("new_user") is True
    mgr.add_message("new_user", "user", "hello")
    assert mgr.is_first_interaction("new_user") is False

def test_clear_removes_session():
    mgr = SessionManager()
    mgr.get_or_create("user_1")
    mgr.clear("user_1")
    assert mgr.is_first_interaction("user_1") is True

def test_expired_session_is_cleaned():
    mgr = SessionManager(expire_minutes=0)  # immediate expiry
    mgr.get_or_create("user_1")
    time.sleep(0.1)
    assert mgr.is_first_interaction("user_1") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_session_manager.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write the implementation**

```python
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Session:
    user_id: str
    messages: List[dict] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """Manage per-user conversation sessions with expiry and max rounds."""

    def __init__(self, max_rounds: int = 10, expire_minutes: int = 30):
        self._sessions: Dict[str, Session] = {}
        self.max_rounds = max_rounds
        self.expire_seconds = expire_minutes * 60

    def get_or_create(self, user_id: str) -> Session:
        self._cleanup_expired()
        if user_id not in self._sessions:
            self._sessions[user_id] = Session(user_id=user_id)
        return self._sessions[user_id]

    def add_message(self, user_id: str, role: str, content: str) -> None:
        session = self.get_or_create(user_id)
        session.messages.append({"role": role, "content": content})
        session.last_active = time.time()
        max_messages = self.max_rounds * 2
        if len(session.messages) > max_messages:
            session.messages = session.messages[-max_messages:]

    def is_first_interaction(self, user_id: str) -> bool:
        session = self.get_or_create(user_id)
        return len(session.messages) == 0

    def get_history(self, user_id: str) -> List[dict]:
        session = self.get_or_create(user_id)
        return session.messages.copy()

    def clear(self, user_id: str) -> None:
        self._sessions.pop(user_id, None)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            uid for uid, s in self._sessions.items()
            if now - s.last_active > self.expire_seconds
        ]
        for uid in expired:
            del self._sessions[uid]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_session_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add phone-card-sales-bot/src/session/manager.py phone-card-sales-bot/tests/test_session_manager.py
git commit -m "feat: add session manager with expiry and round limits"
```

---

### Task 4: Order Stub

**Files:**
- Create: `phone-card-sales-bot/src/order/stub.py`
- Create: `phone-card-sales-bot/tests/test_order_stub.py`

- [ ] **Step 1: Write the test**

```python
from src.order.stub import OrderStub

def test_create_order_returns_placeholder():
    stub = OrderStub()
    result = stub.create_order("user_1", "campus_card")
    assert result["success"] is False
    assert "下单功能" in result["message"]

def test_create_order_accepts_customer_info():
    stub = OrderStub()
    result = stub.create_order("user_1", "campus_card",
                                customer_info={"name": "test"})
    assert result["success"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_order_stub.py -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
from typing import Dict, Optional


class OrderStub:
    """订单接口桩位 - 后续替换为真实订单系统对接"""

    def create_order(self, user_id: str, product_id: str,
                     customer_info: Optional[Dict] = None) -> Dict:
        # TODO: 对接真实订单系统
        return {
            "success": False,
            "message": "下单功能暂时还没接好，你可以先加我联系方式，我帮你登记～",
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_order_stub.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add phone-card-sales-bot/src/order/stub.py phone-card-sales-bot/tests/test_order_stub.py
git commit -m "feat: add order stub with placeholder response"
```

---

### Task 5: AI Prompts

**Files:**
- Create: `phone-card-sales-bot/src/ai/prompts.py`
- Create: `phone-card-sales-bot/tests/test_prompts.py`

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_prompts.py -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
from typing import Dict, List


def build_system_prompt(product: Dict) -> str:
    """Build system prompt with product knowledge and human-like persona."""
    p = product["product"]

    prompt = f"""你是一个阿坝师范学院大二学生，正在QQ上给新生介绍校园电话卡。记住：你是真人学长/学姐，不是客服，不是机器人。

你的核心目标是回答新生问题，介绍电话卡，引导下单。

【说话风格】
- 用QQ聊天的方式说话，自然口语化
- 可以用"嗯嗯"、"对的"、"哈哈"、"～"这些语气，但不要过度
- 不要用"您好"、"尊敬的"这类正式用语
- 不要用"首先/其次/第一/第二"这种结构化的表述
- 不要一次性发太长的消息，短句为主
- 可以适当用"hh"、"真的假的"等网络用语，适度
- 被拒绝就说"好嘞"、"没事"之类，不要纠缠
- 可以偶尔反问对方，像朋友聊天一样

【产品信息 - 牢记以下内容】
- 套餐名称：{p['name']}
- 月费：{p['price']}元/月
- 流量：{p['data']}
- 每月送{p['membership']['count']}个会员：可以从以下平台自选 - {', '.join(p['membership']['platforms'])}
- 买了卡可以用校园网
- 卡自带宿舍门禁功能
- 面向{p['target']}

【常见问题回答要点】
"""
    for item in p.get("faq", []):
        prompt += f"\n问：{item['q']}\n答：{item['a']}\n"

    prompt += """
【重要规则】
1. 回答要简短自然，像真人聊天
2. 不要一次性把产品所有卖点都说完，对方问什么答什么
3. 如果对方对某个点感兴趣，可以多展开说说
4. 如果对方问无关的问题，礼貌拉回正题
5. 注意150G是全国通用，600G是校园流量，别混淆了
6. 对方表现出购买意向时，可以问他们要办卡的联系方式
7. 如果对方要求下单，告诉对方稍后会有办理指引"""

    return prompt


def build_messages(product: Dict, history: List[Dict],
                   user_message: str) -> List[Dict]:
    """Build full messages list for LLM API call."""
    messages = [{"role": "system", "content": build_system_prompt(product)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_prompts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add phone-card-sales-bot/src/ai/prompts.py phone-card-sales-bot/tests/test_prompts.py
git commit -m "feat: add system prompt builder with product knowledge"
```

---

### Task 6: AI Service

**Files:**
- Create: `phone-card-sales-bot/src/ai/service.py`

- [ ] **Step 1: Write the implementation**

```python
from typing import Dict, List, Optional

import httpx


class AIService:
    """LLM API client (OpenAI-compatible)."""

    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.7, max_tokens: int = 1024):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def chat(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Send chat completion request and return assistant's reply."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
```

- [ ] **Step 2: Commit**

```bash
git add phone-card-sales-bot/src/ai/service.py
git commit -m "feat: add AI service for LLM API calls"
```

---

### Task 7: WS Adapter (NapCatQQ WebSocket)

**Files:**
- Create: `phone-card-sales-bot/src/adapter/websocket_client.py`

- [ ] **Step 1: Write the implementation**

```python
import json
import asyncio
import logging
from typing import Callable, Awaitable, Optional

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class NapCatWSAdapter:
    """WebSocket server that receives/sends messages via NapCatQQ (OneBot v11)."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 path: str = "/onebot/v11/ws"):
        self.host = host
        self.port = port
        self.path = path
        self._ws: Optional[WebSocketServerProtocol] = None
        self.on_message: Optional[Callable[[dict], Awaitable[None]]] = None

    async def start(self) -> None:
        """Start WebSocket server and wait for NapCatQQ connection."""

        async def handler(websocket: WebSocketServerProtocol):
            self._ws = websocket
            logger.info("NapCatQQ connected")
            try:
                async for raw in websocket:
                    data = json.loads(raw)
                    logger.debug("Received: %s", data)
                    if self.on_message:
                        asyncio.create_task(self.on_message(data))
            except websockets.exceptions.ConnectionClosed:
                logger.warning("NapCatQQ disconnected")
                self._ws = None

        async with websockets.serve(handler, self.host, self.port):
            logger.info(f"WS server started on ws://{self.host}:{self.port}{self.path}")
            await asyncio.Future()  # run forever

    async def send_message(self, user_id: Optional[int] = None,
                           group_id: Optional[int] = None,
                           message: str = "") -> bool:
        """Send a QQ message via OneBot v11 API."""
        if not self._ws:
            logger.error("No NapCatQQ connection available")
            return False

        payload = {
            "action": "send_msg",
            "params": {
                "message": message,
            },
        }
        if group_id:
            payload["params"]["group_id"] = group_id
        elif user_id:
            payload["params"]["user_id"] = user_id

        await self._ws.send(json.dumps(payload))
        return True
```

- [ ] **Step 2: Commit**

```bash
git add phone-card-sales-bot/src/adapter/websocket_client.py
git commit -m "feat: add WebSocket adapter for NapCatQQ OneBot v11 protocol"
```

---

### Task 8: Message Handler

**Files:**
- Create: `phone-card-sales-bot/src/handler/message.py`
- Create: `phone-card-sales-bot/tests/test_message_handler.py`

- [ ] **Step 1: Write the tests**

```python
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
    text = "流量卡很划算的。一个月48块钱。750G流量。"
    result = MessageHandler._split_message(text, 15)
    assert len(result) >= 3
    assert all(len(s.strip()) <= 16 for s in result)  # allow 1 char over

def test_split_message_long_no_punct():
    text = "a" * 100
    result = MessageHandler._split_message(text, 30)
    assert len(result) == 4  # 100/30 = 4 segments
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_message_handler.py -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
import asyncio
import logging
from typing import Dict, List, Optional

from src.ai.prompts import build_messages, build_system_prompt
from src.ai.service import AIService
from src.order.stub import OrderStub
from src.session.manager import SessionManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """Route incoming QQ messages, orchestrate AI response, handle reply."""

    def __init__(self, session_mgr: SessionManager, ai_service: AIService,
                 order_stub: OrderStub, ws_adapter: "NapCatWSAdapter",
                 product: dict, config: dict):
        self.session_mgr = session_mgr
        self.ai_service = ai_service
        self.order_stub = order_stub
        self.ws_adapter = ws_adapter
        self.product = product
        self.config = config
        self.system_prompt = build_system_prompt(product)

        # Purchase intent keywords (simple detection)
        self.purchase_keywords = ["办", "买", "下单", "怎么买", "怎么办理", "要"]

    async def handle(self, payload: dict) -> None:
        """Process an incoming OneBot v11 message event."""
        msg_type = payload.get("message_type")
        user_id = payload.get("user_id")
        group_id = payload.get("group_id")
        message = self._extract_text(payload.get("message", []))

        if not message or not user_id:
            return

        # Group messages: only respond if @bot or trigger keywords
        if msg_type == "group":
            if not self._should_respond(payload, message):
                return

        logger.info(f"Handling message from {user_id}: {message[:50]}")

        # Build context and call LLM
        history = self.session_mgr.get_history(str(user_id))
        messages = build_messages(self.product, history, message)

        reply = await self.ai_service.chat(messages)
        if not reply:
            return

        # Detect purchase intent
        if self._is_purchase_intent(message):
            order_result = self.order_stub.create_order(str(user_id), "campus_card")
            reply += f"\n\n{order_result['message']}"

        # Save to session
        self.session_mgr.add_message(str(user_id), "user", message)
        self.session_mgr.add_message(str(user_id), "assistant", reply)

        # Send reply with optional splitting
        await self._send_reply(user_id, group_id, msg_type, reply)

    def _is_purchase_intent(self, message: str) -> bool:
        return any(kw in message for kw in self.purchase_keywords)

    async def _send_reply(self, user_id: int, group_id: Optional[int],
                          msg_type: Optional[str], reply: str) -> None:
        settings = self.config.get("human_like", {})
        split_enabled = settings.get("enable_message_split", True)
        max_len = settings.get("max_segment_length", 80)
        delay = settings.get("split_delay", 0.8)

        if split_enabled and len(reply) > max_len:
            segments = self._split_message(reply, max_len)
            for i, seg in enumerate(segments):
                stripped = seg.strip()
                if stripped:
                    await self._send(user_id, group_id, msg_type, stripped)
                    if i < len(segments) - 1:
                        await asyncio.sleep(delay)
        else:
            await self._send(user_id, group_id, msg_type, reply)

    async def _send(self, user_id: int, group_id: Optional[int],
                    msg_type: Optional[str], text: str) -> None:
        if msg_type == "group":
            await self.ws_adapter.send_message(group_id=group_id, message=text)
        else:
            await self.ws_adapter.send_message(user_id=user_id, message=text)

    def _should_respond(self, payload: dict, message: str) -> bool:
        """Determine if bot should respond to a group message."""
        raw_msg = payload.get("raw_message", "")
        bot_qq = str(self.config.get("bot", {}).get("qq", ""))
        if bot_qq and f"[CQ:at,qq={bot_qq}]" in raw_msg:
            return True

        keywords = self.config.get("bot", {}).get("trigger_keywords", [])
        for kw in keywords:
            if kw in message:
                return True
        return False

    def _extract_text(self, message: list) -> str:
        """Extract plain text from OneBot v11 array format message."""
        texts = []
        for seg in message:
            if seg.get("type") == "text":
                texts.append(seg.get("data", {}).get("text", ""))
        return "".join(texts).strip()

    @staticmethod
    def _split_message(text: str, max_len: int) -> List[str]:
        """Split long message at punctuation boundaries near max_len."""
        if len(text) <= max_len:
            return [text]

        segments = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                segments.append(remaining)
                break

            split_at = -1
            for p in ["。", "！", "？", "\n", "，", "；"]:
                idx = remaining.rfind(p, 0, max_len)
                if idx > split_at:
                    split_at = idx

            if split_at <= 0:
                split_at = max_len

            segments.append(remaining[:split_at + 1])
            remaining = remaining[split_at + 1:]

        return segments
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd phone-card-sales-bot && python -m pytest tests/test_message_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add phone-card-sales-bot/src/handler/message.py phone-card-sales-bot/tests/test_message_handler.py
git commit -m "feat: add message handler with routing, splitting, AI orchestration"
```

---

### Task 9: Main entry point

**Files:**
- Create: `phone-card-sales-bot/main.py`
- Create: `phone-card-sales-bot/.env` (from `.env.example`)

- [ ] **Step 1: Write the implementation**

```python
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from src.adapter.websocket_client import NapCatWSAdapter
from src.ai.service import AIService
from src.config_loader import load_config
from src.handler.message import MessageHandler
from src.order.stub import OrderStub
from src.session.manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    base_dir = Path(__file__).parent
    config = load_config(base_dir)
    settings = config["settings"]

    # Initialize components
    ws_adapter = NapCatWSAdapter(
        host=settings["server"]["host"],
        port=settings["server"]["port"],
        path=settings["server"].get("ws_path", "/onebot/v11/ws"),
    )

    ai_service = AIService(
        api_key=settings["llm"]["api_key"],
        base_url=settings["llm"]["base_url"],
        model=settings["llm"]["model"],
        temperature=settings["llm"].get("temperature", 0.7),
        max_tokens=settings["llm"].get("max_tokens", 1024),
    )

    session_mgr = SessionManager(
        max_rounds=settings["session"].get("max_rounds", 10),
        expire_minutes=settings["session"].get("expire_minutes", 30),
    )

    order_stub = OrderStub()
    product = config["product"]

    handler = MessageHandler(
        session_mgr=session_mgr,
        ai_service=ai_service,
        order_stub=order_stub,
        ws_adapter=ws_adapter,
        product=product,
        config=settings,
    )

    ws_adapter.on_message = handler.handle

    logger.info("Starting Phone Card Sales Bot...")
    logger.info(f"LLM: {settings['llm']['model']} @ {settings['llm']['base_url']}")
    logger.info(f"WS server: ws://{settings['server']['host']}:{settings['server']['port']}{settings['server'].get('ws_path', '/onebot/v11/ws')}")

    try:
        asyncio.run(ws_adapter.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `.env` from example**

```bash
cp phone-card-sales-bot/.env.example phone-card-sales-bot/.env
```

- [ ] **Step 3: Run all tests to verify**

Run: `cd phone-card-sales-bot && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Verify service starts without errors**

Run: `cd phone-card-sales-bot && timeout 3 python main.py 2>&1 || true`
Expected: Service logs "Starting Phone Card Sales Bot..." and WS server info (then exits from timeout)

- [ ] **Step 5: Commit**

```bash
git add phone-card-sales-bot/main.py phone-card-sales-bot/.env
git commit -m "feat: add main entry point wiring all components"
```

---

### Task 10: NapCatQQ setup guide

**Files:**
- Create: `phone-card-sales-bot/NAPCAT_SETUP.md`

- [ ] **Step 1: Write the setup guide**

````markdown
# NapCatQQ 配置指南

## 1. 安装 NapCatQQ Desktop

从 https://github.com/NapNeko/NapCatQQ/releases 下载 NapCatQQ Desktop 版本并安装。

## 2. 配置反向 WebSocket

在 NapCatQQ 的配置目录中找到 `onebot11_<你的QQ号>.json`，修改以下配置：

```json
{
  "wsReverseUrls": ["ws://127.0.0.1:8765/onebot/v11/ws"],
  "enableWsReverse": true,
  "messagePostFormat": "array",
  "heartInterval": 30000
}
```

## 3. 启动顺序

1. 先启动本服务：`cd phone-card-sales-bot && python main.py`
2. 再启动 NapCatQQ Desktop
3. 确认日志输出 "NapCatQQ connected"

## 4. 验证

向机器人 QQ 发送消息，检查终端是否有消息日志输出。
````

- [ ] **Step 2: Verify the guide renders correctly**

```bash
head -5 phone-card-sales-bot/NAPCAT_SETUP.md
```

- [ ] **Step 3: Commit**

```bash
git add phone-card-sales-bot/NAPCAT_SETUP.md
git commit -m "docs: add NapCatQQ setup guide"
```
