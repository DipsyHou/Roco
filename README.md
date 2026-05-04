# Roco CLI（Python 引擎 + 联机）

原版 TS/React/WebSocket 的精简移植：**游戏规则与数值在 `roco/` 下用 Python 实现**，通过 **WebSocket** 联机；命令行客户端用于操作。

## 增益 / 减益 / 标记清单

见 [`docs/effects-and-marks.md`](docs/effects-and-marks.md)。

## 安装

```bash
cd cli
pip install -r requirements.txt
```

或将包安装为可编辑：

```bash
cd cli
pip install -e .
```

## 启动服务器

默认监听 **3001**（可用环境变量 `PORT`）：

```bash
cd cli
python -m roco server
# 或: roco-server
```

## 启动 CLI 客户端

```bash
cd cli
python -m roco client 我的昵称
# 或: roco-client 我的昵称
```

连接地址：`ws://ROCO_HOST:ROCO_PORT`（默认 `localhost:3001`）。

## 对战流程（CLI）

1. 大厅：`c` 创建房间（记下房间号）、`jABCDEF` 加入、`m` 随机匹配。  
2. 阵容：输入 4 个模板 **id**（`flora` `clawdragon` `chaosling` `starweaver`），空格分隔。  
3. 首发：输入 1～4 个 **uniqueId**（界面列出）。  
4. 战斗：按提示选择场上精灵与动作；技能多数需要再输入目标 **uniqueId**（服务端会校验）。

## 自动化测试（房间 / 选阵容）

```bash
cd cli
python tests/test_room_flow.py
```

## 与原仓库关系

- 协议消息类型对齐原 `shared/src/types/protocol.ts` 的字符串（如 `submit_action`、`battle_start`）。  
- 数值与技能逻辑对齐原服务端实现；前端 Canvas 已移除，仅保留 CLI。
