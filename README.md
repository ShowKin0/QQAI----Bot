# QQ AI Bot

基于 [NapCatQQ Desktop](https://github.com/NapNeko/NapCatQQ) + Python + LLM 的可定制 AI QQ 机器人。

核心特点：通过 **Web 管理面板** 可视化配置多个角色预设，机器人根据当前激活的预设 persona 进行回复。不同场景只需切换预设，无需改代码。

## 功能

- **Web 管理面板** — 浏览器中管理所有角色预设，实时切换、编辑提示词和参数
- **多角色预设** — 每个预设独立配置系统提示词、触发关键词、会话参数、备注过滤规则
- **AI 驱动对话** — 接入 DeepSeek / OpenAI 兼容 API，支持任意自定义 persona
- **真人化回复** — 长消息自动拆分、随机延迟、打字速度模拟，回复更自然
- **群聊 + 私聊** — 群聊支持关键词/ @ 触发，私聊自动回复
- **产品知识库** — YAML 配置外部知识，AI 回复时自动引用，修改无需重启
- **备注过滤** — 按 QQ 好友备注前缀精准控制回复目标

## 架构

```
┌─────────────────────────────────────────────┐
│              QQ Bot (Python)                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │WS Adapter│→ │  Session │→ │AI Service │  │
│  │(WebSocket)│  │ Manager  │  │(LLM API)  │  │
│  └────┬─────┘  └──────────┘  └─────┬─────┘  │
│       │                            │         │
│  ┌────▼─────┐  ┌──────────┐  ┌────▼──────┐  │
│  │ Message  │← │ Product  │  │  Order    │  │
│  │ Handler  │  │Knowledge  │  │  Stub     │  │
│  └──────────┘  └──────────┘  └───────────┘  │
└──────────────────────┬──────────────────────┘
                       │ 反向 WebSocket (OneBot v11)
          ┌────────────▼──────────────────┐
          │      NapCatQQ Desktop         │
          └───────────────────────────────┘
```

## 快速开始

### 前置条件

- Python 3.10+
- NapCatQQ Desktop（已包含在仓库中）
- LLM API Key（DeepSeek / OpenAI 兼容）

### 安装

```bash
# 1. 进入项目目录
cd phone-card-sales-bot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 配置 NapCatQQ

编辑 NapCatQQ 的 `onebot11_<QQ号>.json`，添加反向 WebSocket 地址：

```json
{
  "wsReverseUrls": ["ws://127.0.0.1:8765/onebot/v11/ws"],
  "enableWsReverse": true,
  "messagePostFormat": "array",
  "heartInterval": 30000
}
```

### 启动

```bash
cd phone-card-sales-bot
python main.py
```

启动顺序：先启动 Python 服务，再启动 NapCatQQ Desktop。

打开浏览器访问 `http://localhost:8767` 进入管理面板。

## 配置

### `config/settings.yaml`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `server.host` | WS 服务监听地址 | `0.0.0.0` |
| `server.port` | WS 服务端口 | `8765` |
| `llm.api_key` | LLM API 密钥 | `${LLM_API_KEY}` |
| `llm.base_url` | LLM API 地址 | `${LLM_BASE_URL}` |
| `llm.model` | 模型名称 | `deepseek-chat` |
| `session.max_rounds` | 最大对话轮数 | `10` |
| `session.expire_minutes` | 会话过期时间 | `7200` |

### `config/product.yaml`

预设可引用的外部知识库，例如产品信息、FAQ 等。修改后自动生效，无需重启。

## 角色预设系统

通过 Web 面板（`http://localhost:8767`）可视化管理预设，支持：

- 创建、编辑、删除预设
- 预设内容：**系统提示词** + **触发关键词** + **会话参数**
- 一键切换激活预设
- 预设文件保存在 `presets/` 目录（YAML 格式），可直接版本管理

内置预设示例：

| 预设 | 说明 |
|------|------|
| `phone-card-sales` | 校园电话卡销售（学长/学姐人设，附带阶段性话术和返现策略） |
| `psychology-teacher` | 心理老师角色 |
| `empty-template` | 空白模板，可自由定义 |

每个预设独立配置：角色提示词、触发关键词、备注过滤前缀、最大对话轮数、会话过期时间、首条延迟、打字速度、最大延迟等。

## 项目结构

```
phone-card-sales-bot/
├── main.py                        # 服务入口
├── webui.py                       # Web 管理面板
├── requirements.txt               # Python 依赖
├── .env                           # API Key 等敏感配置
├── config/
│   ├── settings.yaml              # 服务配置
│   └── product.yaml               # 知识库（预设可引用）
├── presets/                       # 角色预设（YAML）
├── src/
│   ├── adapter/
│   │   └── websocket_client.py    # WS 适配器（OneBot v11）
│   ├── ai/
│   │   ├── service.py             # LLM API 调用
│   │   └── prompts.py             # System prompt 构建
│   ├── session/
│   │   └── manager.py             # 会话管理
│   ├── handler/
│   │   └── message.py             # 消息路由与处理
│   ├── order/
│   │   └── stub.py                # 订单接口桩
│   ├── config_loader.py           # 配置加载
│   └── preset_manager.py          # 预设管理
├── docs/                          # 文档
└── NapCatQQ Desktop/              # NapCatQQ 客户端
```

## 技术栈

- **Python** — 主服务端
- **websockets** — WebSocket 服务端（OneBot v11 协议）
- **FastAPI** — Web 管理面板
- **httpx** — LLM API 调用
- **PyYAML** — 配置加载
- **pytest** — 测试
- **NapCatQQ** — QQ 客户端

## 开发

```bash
# 运行测试
pytest

# 启动管理面板（独立运行）
python webui.py
```

## License

MIT
