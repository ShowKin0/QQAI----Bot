#!/usr/bin/env python3
"""Web UI for managing QQ Bot presets.

Usage: python webui.py
Opens at http://localhost:8767
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.preset_manager import PresetManager

app = FastAPI(title="QQ Bot 管理面板")
pm = PresetManager()


# ── API ──

@app.get("/api/presets")
def list_presets():
    names = pm.list_presets()
    active = pm.get_active_name()
    result = []
    for name in names:
        preset = pm.get_preset(name)
        result.append({
            "name": name,
            "label": preset.get("name", name) if preset else name,
            "active": name == active,
        })
    return {"presets": result, "active": active}


@app.get("/api/presets/{name}")
def get_preset(name: str):
    data = pm.get_preset(name)
    if not data:
        raise HTTPException(404, f"Preset '{name}' not found")
    return {"name": name, **data}


class PresetUpdate(BaseModel):
    name: str
    prompt: str
    remark_prefix: str = ""
    remark_filter_enabled: bool = False
    trigger_keywords: list = []
    max_rounds: int = 10
    expire_minutes: int = 7200
    first_msg_delay: int = 10
    typing_speed: int = 50
    max_delay: int = 30


@app.put("/api/presets/{name}")
def update_preset(name: str, body: PresetUpdate):
    data = {
        "name": body.name,
        "prompt": body.prompt,
        "settings": {
            "remark_prefix": body.remark_prefix,
            "remark_filter_enabled": body.remark_filter_enabled,
            "trigger_keywords": body.trigger_keywords,
            "max_rounds": body.max_rounds,
            "expire_minutes": body.expire_minutes,
            "first_msg_delay": body.first_msg_delay,
            "typing_speed": body.typing_speed,
            "max_delay": body.max_delay,
        },
    }
    pm.save_preset(name, data)
    return {"ok": True}


@app.post("/api/presets")
def create_preset(body: PresetUpdate):
    name = body.name
    if pm.get_preset(name):
        raise HTTPException(409, f"Preset '{name}' already exists")
    data = {
        "name": body.name,
        "prompt": body.prompt,
        "settings": {
            "remark_prefix": body.remark_prefix,
            "remark_filter_enabled": body.remark_filter_enabled,
            "trigger_keywords": body.trigger_keywords,
            "max_rounds": body.max_rounds,
            "expire_minutes": body.expire_minutes,
            "first_msg_delay": body.first_msg_delay,
            "typing_speed": body.typing_speed,
            "max_delay": body.max_delay,
        },
    }
    pm.save_preset(name, data)
    return {"ok": True}


@app.post("/api/presets/{name}/activate")
def activate_preset(name: str):
    ok = pm.set_active(name)
    if not ok:
        raise HTTPException(404, f"Preset '{name}' not found")
    return {"ok": True}


@app.delete("/api/presets/{name}")
def delete_preset(name: str):
    ok = pm.delete_preset(name)
    if not ok:
        raise HTTPException(400, f"Cannot delete active preset or preset not found")
    return {"ok": True}


# ── Frontend ──

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QQ Bot 管理面板</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background:#f5f5f5; color:#333; height:100vh; display:flex; flex-direction:column; }
header { background:#1a73e8; color:#fff; padding:12px 24px; display:flex; align-items:center; gap:16px; flex-shrink:0; }
header h1 { font-size:18px; font-weight:500; }
header .badge { background:rgba(255,255,255,0.2); padding:4px 12px; border-radius:12px; font-size:13px; }
.container { display:flex; flex:1; overflow:hidden; }
.sidebar { width:260px; background:#fff; border-right:1px solid #e0e0e0; display:flex; flex-direction:column; flex-shrink:0; }
.sidebar h2 { font-size:14px; font-weight:600; padding:16px 16px 8px; color:#666; text-transform:uppercase; letter-spacing:0.5px; }
.preset-list { flex:1; overflow-y:auto; padding:4px 8px; }
.preset-item { padding:10px 12px; border-radius:8px; cursor:pointer; display:flex; align-items:center; justify-content:space-between; margin-bottom:2px; transition:background 0.15s; }
.preset-item:hover { background:#e8f0fe; }
.preset-item.active { background:#e8f0fe; font-weight:500; }
.preset-item .label { font-size:14px; }
.preset-item .active-tag { font-size:11px; color:#1a73e8; background:#e8f0fe; padding:2px 8px; border-radius:10px; }
.preset-item .del-btn { font-size:16px; color:#999; background:none; border:none; cursor:pointer; padding:0 4px; opacity:0; }
.preset-item:hover .del-btn { opacity:1; }
.preset-item .del-btn:hover { color:#d93025; }
.sidebar-footer { padding:12px; border-top:1px solid #e0e0e0; }
.sidebar-footer button { width:100%; padding:8px; background:#1a73e8; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px; }
.sidebar-footer button:hover { background:#1765cc; }
.main { flex:1; overflow-y:auto; padding:24px; }
.main h2 { font-size:16px; margin-bottom:16px; }
.form-group { margin-bottom:16px; }
.form-group label { display:block; font-size:13px; font-weight:500; color:#555; margin-bottom:4px; }
.form-group textarea { width:100%; min-height:300px; padding:12px; font-size:14px; font-family:inherit; border:1px solid #ddd; border-radius:8px; resize:vertical; line-height:1.6; }
.form-group textarea:focus { outline:none; border-color:#1a73e8; }
.form-row { display:flex; gap:12px; flex-wrap:wrap; }
.form-row .form-group { flex:1; min-width:120px; }
.form-group input, .form-group select { width:100%; padding:8px 10px; font-size:14px; border:1px solid #ddd; border-radius:6px; }
.form-group input:focus { outline:none; border-color:#1a73e8; }
.form-group .toggle-wrap { display:flex; align-items:center; gap:8px; }
.form-group .toggle-wrap input[type=checkbox] { width:auto; }
.actions { display:flex; gap:8px; margin-top:8px; }
.actions button { padding:8px 20px; border-radius:6px; font-size:14px; cursor:pointer; border:none; }
.btn-primary { background:#1a73e8; color:#fff; }
.btn-primary:hover { background:#1765cc; }
.btn-save { background:#34a853; color:#fff; }
.btn-save:hover { background:#2d9249; }
.btn-switch { background:#fbbc04; color:#333; }
.btn-switch:hover { background:#e8ab00; }
.empty-state { text-align:center; padding:60px 20px; color:#999; }
.empty-state p { font-size:14px; margin-top:8px; }
.toast { position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:#333; color:#fff; padding:10px 24px; border-radius:8px; font-size:14px; opacity:0; transition:opacity 0.3s; pointer-events:none; }
.toast.show { opacity:1; }
</style>
</head>
<body>
<header>
  <h1>QQ Bot 管理面板</h1>
  <span class="badge" id="activeBadge">加载中...</span>
</header>
<div class="container">
  <div class="sidebar">
    <h2>角色预设</h2>
    <div class="preset-list" id="presetList"></div>
    <div class="sidebar-footer">
      <button onclick="createPreset()">+ 新建预设</button>
    </div>
  </div>
  <div class="main" id="editor">
    <div class="empty-state">
      <div style="font-size:48px;margin-bottom:16px;">📋</div>
      <h2>选择一个预设开始编辑</h2>
      <p>左侧列表点击预设名称即可编辑</p>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let currentName = null;

async function api(path, opts={}) {
  const res = await fetch(path, { headers: {'Content-Type':'application/json'}, ...opts });
  if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e.detail || res.statusText); }
  return res.json();
}

function toast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2500); }

async function refreshList() {
  const data = await api('/api/presets');
  const list = document.getElementById('presetList');
  const badge = document.getElementById('activeBadge');
  badge.textContent = '当前: ' + (data.presets.find(p => p.active)?.label || data.active);
  list.innerHTML = data.presets.map(p => `
    <div class="preset-item${p.active ? ' active' : ''}" onclick="selectPreset('${p.name}')">
      <span class="label">${p.label}</span>
      <span style="display:flex;align-items:center;gap:6px;">
        ${p.active ? '<span class="active-tag">使用中</span>' : ''}
        <button class="del-btn" onclick="event.stopPropagation();deletePreset('${p.name}')" title="删除">×</button>
      </span>
    </div>
  `).join('');
  if (currentName && data.presets.some(p => p.name === currentName)) {
    // refresh editor if preset still exists
    selectPreset(currentName);
  }
}

async function selectPreset(name) {
  currentName = name;
  const data = await api(`/api/presets/${name}`);
  const s = data.settings || {};
  document.getElementById('editor').innerHTML = `
    <h2>${data.name || name}</h2>
    <div class="form-group">
      <label>预设名称</label>
      <input id="f_name" value="${data.name || name}" onchange="dirty=true">
    </div>
    <div class="form-group">
      <label>角色提示词 (System Prompt)</label>
      <textarea id="f_prompt" onchange="dirty=true">${escapeHtml(data.prompt || '')}</textarea>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>备注前缀过滤</label>
        <input id="f_prefix" value="${s.remark_prefix || ''}" placeholder="例如: A" onchange="dirty=true">
      </div>
      <div class="form-group">
        <label>&nbsp;</label>
        <div class="toggle-wrap"><input type="checkbox" id="f_filter" ${s.remark_filter_enabled ? 'checked' : ''} onchange="dirty=true"> <span>启用备注过滤</span></div>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>触发关键词 (群聊, 逗号分隔)</label>
        <input id="f_kw" value="${(s.trigger_keywords || []).join(',')}" placeholder="卡,流量" onchange="dirty=true">
      </div>
      <div class="form-group">
        <label>最大对话轮数</label>
        <input type="number" id="f_rounds" value="${s.max_rounds || 10}" onchange="dirty=true">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>会话过期 (分钟)</label>
        <input type="number" id="f_expire" value="${s.expire_minutes || 7200}" onchange="dirty=true">
      </div>
      <div class="form-group">
        <label>首条延迟 (秒)</label>
        <input type="number" id="f_firstDelay" value="${s.first_msg_delay || 15}" onchange="dirty=true">
      </div>
      <div class="form-group">
        <label>打字速度 (字/分钟)</label>
        <input type="number" id="f_speed" value="${s.typing_speed || 50}" onchange="dirty=true">
      </div>
      <div class="form-group">
        <label>最大延迟 (秒)</label>
        <input type="number" id="f_maxDelay" value="${s.max_delay || 30}" onchange="dirty=true">
      </div>
    </div>
    <div class="actions">
      <button class="btn-save" onclick="savePreset('${name}')">💾 保存</button>
      <button class="btn-switch" onclick="activatePreset('${name}')">▶ 切换到此预设</button>
    </div>
  `;
  document.querySelectorAll('.preset-item').forEach(el => el.classList.toggle('active', el.querySelector('.label')?.textContent === (data.name || name)));
}

function escapeHtml(text) {
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function savePreset(name) {
  const get = id => document.getElementById(id);
  const kw = get('f_kw').value.split(',').map(s => s.trim()).filter(Boolean);
  const body = {
    name: get('f_name').value,
    prompt: get('f_prompt').value,
    remark_prefix: get('f_prefix').value,
    remark_filter_enabled: get('f_filter').checked,
    trigger_keywords: kw,
    max_rounds: parseInt(get('f_rounds').value) || 10,
    expire_minutes: parseInt(get('f_expire').value) || 7200,
    first_msg_delay: parseInt(get('f_firstDelay').value) || 15,
    typing_speed: parseInt(get('f_speed').value) || 50,
    max_delay: parseInt(get('f_maxDelay').value) || 30,
  };
  if (name !== body.name && await presetExists(body.name)) {
    toast('名称已存在，换个名字');
    return;
  }
  await api(`/api/presets/${name}`, { method:'PUT', body: JSON.stringify(body) });
  toast('已保存');
  refreshList();
}

async function presetExists(name) {
  try { const data = await api(`/api/presets/${name}`); return !!data; } catch(e) { return false; }
}

async function activatePreset(name) {
  await api(`/api/presets/${name}/activate`, { method:'POST' });
  toast('已切换到: ' + name);
  refreshList();
}

async function deletePreset(name) {
  if (!confirm(`确定删除 "${name}" ？`)) return;
  try {
    await api(`/api/presets/${name}`, { method:'DELETE' });
    toast('已删除: ' + name);
    if (currentName === name) {
      currentName = null;
      document.getElementById('editor').innerHTML = '<div class="empty-state"><div style="font-size:48px;margin-bottom:16px;">📋</div><h2>选择一个预设开始编辑</h2></div>';
    }
    refreshList();
  } catch(e) {
    toast('删除失败: ' + e.message);
  }
}

async function createPreset() {
  const name = prompt('输入预设名称 (英文或拼音，用作文件名):');
  if (!name) return;
  if (await presetExists(name)) { toast('已存在同名预设'); return; }
  const body = {
    name: name,
    prompt: `在这里输入 ${name} 的角色提示词...`,
    trigger_keywords: [],
  };
  await api('/api/presets', { method:'POST', body: JSON.stringify(body) });
  toast('已创建: ' + name);
  refreshList();
  selectPreset(name);
}

refreshList();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


def run():
    uvicorn.run(app, host="0.0.0.0", port=8767, log_level="info")


if __name__ == "__main__":
    run()
