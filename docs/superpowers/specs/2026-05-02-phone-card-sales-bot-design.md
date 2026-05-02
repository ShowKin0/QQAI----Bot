# Phone Card Sales QQ Bot — 设计文档

## 概述

基于 NapCatQQ Desktop + 独立 Python 服务，对接 QQ 的 AI 电话卡销售机器人。AI 以「学长/学姐」人设，面向阿坝师范学院新生销售校园流量卡。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                  Phone Card Sales Bot (Python)           │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │  WS Adapter   │    │   Session     │    │  AI Service │  │
│  │  (websocket)  │───▶│   Manager     │───▶│  (LLM API) │  │
│  └──────┬───────┘    └──────────────┘    └──────┬─────┘  │
│         │                                        │         │
│  ┌──────▼───────┐    ┌────────────────┐    ┌──────▼─────┐  │
│  │  Message     │    │   Product      │    │  Order     │  │
│  │  Handler     │◄───│   Knowledge    │    │  Stub      │  │
│  └──────────────┘    └────────────────┘    └────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ 反向 WebSocket (OneBot v11)
          ┌─────────────▼──────────────────────────────┐
          │          NapCatQQ Desktop                    │
          └────────────────────────────────────────────┘
```

### 核心组件

| 模块 | 职责 |
|------|------|
| WS Adapter | 反向 WS 连接 NapCatQQ，收发 OneBot v11 消息 |
| Session Manager | 管理每个 QQ 用户的对话上下文（最近 N 轮） |
| AI Service | 调用 LLM API（OpenAI 兼容），组装 prompt + 产品知识 |
| Message Handler | 消息路由、意图识别、业务逻辑编排 |
| Product Knowledge | YAML 配置文件，存产品信息和 FAQ |
| Order Stub | 订单接口桩位，后续对接真实订单系统 |

## 通信方式

- NapCatQQ 配置反向 WebSocket 连接本服务：`ws://127.0.0.1:8765/onebot/v11/ws`
- 消息格式：OneBot v11 array 格式
- 本服务作为 WS 服务端，NapCatQQ 作为客户端主动连接

## AI 人设设计（核心）

### 身份设定

- **角色**：阿坝师范学院大二/大三的学长/学姐
- **目标**：帮新生介绍校园电话卡，引导下单
- **语气**：自然口语化中文，QQ 聊天风格

### 语言风格要求

- 使用 QQ 常见语气词："嗯嗯"、"对的"、"哈哈"、"确实"、"～"
- 偶尔发短句，不一口气说完一大段
- 不会使用"您好"、"尊敬的"等正式/敬语表达
- 适当使用"hh"、"真的假的"等网络用语（适度）
- 不结构化回复（不用"第一"、"第二"、"首先"、"然后"作列举）
- 不主动使用 Markdown 格式（列表/表格/标题）

### 拟人化回复策略

- **长消息拆分**：超过 80 字符的回复拆成 2-3 条发送，间隔 0.5-1 秒
- **不强行推销**：被拒绝时自然回应"好嘞，有需要找我～"，不反复纠缠
- **偶尔反问互动**：像真人聊天一样反问（"你哪个专业的呀？"）
- **不完美主义**：允许偶尔的口语化断句，不需要每句话语法完美

## 产品知识

### 流量卡卖点

| 属性 | 内容 |
|------|------|
| 月费 | 48 元/月 |
| 流量 | 750GB/月（150GB 全国通用 + 600GB 校园区域流量） |
| 会员权益 | 每月可自选 2 款会员（视频/音乐平台，含腾讯视频、爱奇艺、网易云等） |
| 校园网 | 购买后可接入校园网 |
| 门禁功能 | 电话卡自带宿舍开门功能 |
| 目标人群 | 阿坝师范学院新生 |

### 知识管理方式

- `config/product.yaml` 结构化配置，包含产品信息 + FAQ
- 每次 AI 调用时，system prompt 动态加载该配置
- 修改配置即可更新产品信息，无需改代码

## 下单流程（预留）

当前阶段只做接口定义，不实现具体逻辑：

```
AI 识别购买意图 → Order Stub.create_order() → 返回"下单功能开放中"提示
```

后续在 Order Stub 中替换为真实订单系统对接即可。

## 会话管理

- 以 `user_id` 为 key 维护消息历史列表
- 保留最近 10 轮对话（可配置）
- 会话过期时间：30 分钟（可配置）
- 首次对话自动触发欢迎流程

## 消息处理流程

```
QQ用户发送消息
       │
       ▼
NapCatQQ → 反向 WS → WS Adapter
       │ 解析 user_id, message, message_type
       ▼
Message Handler
       │
       ├─▶ 群消息？→ 检查 @机器人 / 含触发关键词 → 否→丢弃
       │                                         → 是→继续
       │
       ├─▶ Session Manager 获取/创建会话上下文
       │
       ├─▶ AI Service 构建 prompt → 调用 LLM API → 返回回复
       │
       ├─▶ 检测到购买意图 → Order Stub（返回占位提示）
       │
       ├─▶ Session Manager 保存本轮对话
       │
       └─▶ WS Adapter 拆分长消息，分段回复用户
```

## 配置结构

### config/settings.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 8765
  ws_path: "/onebot/v11/ws"

llm:
  api_key: "${LLM_API_KEY}"
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
  temperature: 0.7
  max_tokens: 1024

session:
  max_rounds: 10
  expire_minutes: 30

bot:
  name: "校园助手"
  trigger_keywords: ["卡", "流量", "套餐", "电话卡"]

human_like:
  enable_message_split: true
  split_delay: 0.8
  max_segment_length: 80
```

### config/product.yaml

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

## 项目目录结构

```
phone-card-sales-bot/
├── main.py                      # 入口，启动 WS 服务
├── requirements.txt             # Python 依赖
├── .env                         # API Key 等敏感配置
├── config/
│   ├── settings.yaml            # 服务配置
│   └── product.yaml             # 产品知识库
└── src/
    ├── __init__.py
    ├── adapter/
    │   ├── __init__.py
    │   └── websocket_client.py  # WS 适配器
    ├── ai/
    │   ├── __init__.py
    │   ├── service.py           # LLM API 调用
    │   └── prompts.py           # system prompt 构建
    ├── session/
    │   ├── __init__.py
    │   └── manager.py           # 会话管理
    ├── handler/
    │   ├── __init__.py
    │   └── message.py           # 消息路由
    └── order/
        ├── __init__.py
        └── stub.py              # 订单接口桩
```

## 依赖

- `websockets` — WebSocket 服务端，接收 NapCatQQ 连接
- `httpx` — 调用 LLM API
- `pyyaml` — 加载 YAML 配置
- `python-dotenv` — 加载 .env 环境变量
