---
description: 卸载 zcode-hud（还原 app.asar，删除注入）
---
从 ZCode 桌面客户端移除 zcode-hud：还原 pristine app.asar。

执行（resources 目录可写时免授权）：

    python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" unpatch

若提示目录不可写，改用系统授权（会弹出授权框）：

    pkexec python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" unpatch --home "$HOME"

若 `${ZCODE_PLUGIN_ROOT}` 为空，先用 `find ~/.zcode/cli/plugins/cache -maxdepth 4 -type d -name zcode-hud | tail -1` 定位插件根目录。

结果处理：

- 成功：告知用户「✅ 已还原；完全退出并重开 ZCode 后主题与 HUD 消失」。
- 「备份与当前客户端版本不一致」：说明 ZCode 升级过，备份已过期；不要强行还原，提示用户重装 ZCode 或重跑 install 重建备份后再卸载。

用户附加要求：$ARGUMENTS
