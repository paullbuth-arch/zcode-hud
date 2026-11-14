# zcode-hud

ZCode 桌面客户端的「主题 + 动画状态条」二合一插件，在本仓库统一维护。

- **主题**：壁纸取自当前 GNOME 桌面背景，统一轻透玻璃表面，JetBrains Mono + Noto Sans CJK SC 字体链。
- **动画状态条**：vendored 原版 [zcode-token-usage-statusbar](https://github.com/ByteRax/zcode-token-usage-statusbar) v1.5.19（MIT，见 [vendor/UPSTREAM.md](zcode-hud/vendor/UPSTREAM.md)）——输入框下方的玻璃拟态悬浮胶囊：实时 tok/s、本轮/会话/今日用量、逐问速率行、上下文环、悬停明细面板与图表，rAF 跟随、呼吸灯、主题色全量跟随客户端。
- **一次注入**：只改 `out/main/index.js`（追加一行 dynamic import）。wrapper loader 注入主题 CSS 并链式加载 vendored 状态条 loader，没有第二个补丁点。
- **触发式数据层**：原版常驻 python 查询进程（`zusage.py serve`），fs.watch 监听 usage DB 写入才查询，完全空闲时零轮询；只读访问 `~/.zcode/cli/db/db.sqlite`。
- **无钩子、无自动更新、无 MCP、不开 CDP 调试端口**：上游的 SessionStart 自动修复/插件接线已移除，更新通过本仓库维护。

## 命令

| 命令 | 作用 |
|---|---|
| `/install` | 部署运行时资产并注入 app.asar |
| `/uninstall` | 还原 pristine app.asar |
| `/status` | 只读状态检查 |

## 手动执行

```bash
# 1. 部署资产（用户权限）
python3 scripts/install.py deploy

# 2. 打补丁（需要 /opt/ZCode/resources 目录可写；目录不可写时用 pkexec）
python3 scripts/install.py patch
# pkexec python3 scripts/install.py patch --home "$HOME"

# 状态 / 卸载
python3 scripts/install.py status
python3 scripts/install.py unpatch
```

安装后必须**完全退出 ZCode**（不是关闭窗口）再重新打开。

## 网络行为

- 额度查询 / 重置卡 / 自动更新 / 引擎补丁：默认**关闭**（`~/.zcode-ui/zusage/config.json`，⚙ 面板可改）。
- 价表：serve 进程每 12h 拉 models.dev 与汇率（公开数据、无凭据、失败静默用内置价表），上游未提供开关。
- 模型列表拉取 / 提示词增强：仅用户在 ⚙ 面板主动点击时联网。

## 文件布局

```
~/.zcode-ui/
├── hud/
│   ├── inject-main.cjs     # wrapper loader（asar 注入入口）
│   └── theme.css           # 主题样式
├── zusage/                 # vendored 状态条运行时 + config.json + 运行时缓存
├── fonts/                  # JetBrains Mono
└── backups/app.asar.original   # pristine 备份
~/.zcode/v2/wall.png        # 主题壁纸（安装时同步当前桌面壁纸）
```

## 已知边界

- ZCode 通过 RPM 升级会覆盖 `app.asar`，重跑 `/install` 即可重新注入（脚本会检测版本变化并重建备份）。
- 同步上游新版状态条：按 [vendor/UPSTREAM.md](zcode-hud/vendor/UPSTREAM.md) 的步骤替换 vendored 文件后重新 deploy。
- 主题把壁纸画在 `html` 上（而不是应用外壳），顺带修掉了全屏时窗口顶部约 16px 的白色未绘制区域。

## 许可

MIT。vendored 状态条代码 MIT，Copyright (c) 2026 xhwx（ByteRax/zcode-token-usage-statusbar）。
JetBrains Mono 字体遵循 SIL OFL 1.1（`theme/fonts/OFL.txt`）。