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

1. 先启动本服务：

   ```bash
   cd phone-card-sales-bot
   python main.py
   ```

2. 再启动 NapCatQQ Desktop
3. 确认服务端日志输出 "NapCatQQ connected"

## 4. 验证

向机器人 QQ 发送消息，检查终端是否有消息日志输出。
