# Roco

Roco 是一个基于时间轴行动值的精灵对战项目，包含本地桌面版、联机客户端和权威服务端。

## 项目结构

```text
assets/             图片与图标资源
docs/               设计文档与机制说明
roco/
  apps/             桌面 UI 与联机桌面入口
  core/             纯战斗逻辑、AI、精灵逻辑
  net/              联机协议、客户端、远端引擎视图、序列化
tests/              pytest 测试
scripts/            打包与演示脚本
```

## 安装

建议使用 Python 3.10+。

```bash
python -m pip install -e ".[online,test]"
```

如果只运行本地桌面版，也可以直接安装基础包：

```bash
python -m pip install -e .
```

## 运行

本地桌面版：

```bash
roco-desktop
```

联机服务端：

```bash
roco-online-server --host 127.0.0.1 --port 8765
```

联机桌面客户端：

```bash
roco-online-desktop
```

## 测试

```bash
pytest
```

## 分层约定

- `roco.core` 是纯战斗核心，不应依赖 Tkinter、桌面 UI 或服务端 UI。
- `roco.apps` 负责用户界面和交互流程。
- `roco.net` 负责协议、传输、序列化以及远端引擎视图。
- `roco.server` 承载权威联机房间与 WebSocket 服务端。
