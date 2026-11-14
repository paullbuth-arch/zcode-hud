# Vendored upstream: zcode-token-usage-statusbar

- **来源**: https://github.com/ByteRax/zcode-token-usage-statusbar
- **版本**: v1.5.19（release zip，2026-11-13 发布）
- **许可**: MIT，Copyright (c) 2026 xhwx（原文保留在 `zusage/LICENSE`）
- **引入日期**: 2026-11-14，经用户同意并入 zcode-hud 统一维护

## 改动了什么

运行时文件**逐字节保留原版**，仅移除插件级接线（由 zcode-hud 自己的
plugin.json / commands / scripts 取代）：

- `commands/`（/install-overlay /uninstall-overlay /usage）
- `hooks/`（SessionStart 自动修复/提示、prompt-submit）
- `skills/`、`.mcp.json`

保留 `.zcode-plugin/plugin.json`：`plugin-updater.cjs` 初始化时读它做版本
标识（自动更新已在 config 中关闭，不会拉取/安装）。

## 默认关闭的行为（config.json，首次 deploy 写入）

| 开关 | 值 | 效果 |
|---|---|---|
| `quota_enabled` | false | 不解密凭据、不查额度 |
| `reset_badge_enabled` | false | 不查重置卡 |
| `plugin_auto_update` | false | 不自动更新（更新走本仓库） |
| `auto_compact_patch` | false | 不打引擎阈值补丁 |

另外 wrapper loader（`runtime/inject-main.cjs`）设置
`ZCODE_DISABLE_FIXED_REMOTE_DEBUGGING_PORT=1`，不补开 CDP 9229 调试端口。

## 仍会联网的部分

- 价表：serve 常驻进程每 12h 拉 models.dev 与 USD→CNY 汇率（公开数据、
  无凭据、失败静默保留内置价表）——上游未提供开关。
- 模型列表拉取 / 提示词增强：仅用户在 ⚙ 面板主动点击时触发。

## 如何同步上游新版

1. 下载新 release zip，解压出 `plugins/zcode-token-usage-statusbar/`。
2. 用其内容替换本目录，再删除 `commands/ hooks/ skills/ .mcp.json`。
3. 更新本文件的版本号，跑 `python3 scripts/install.py deploy`，重启 ZCode。