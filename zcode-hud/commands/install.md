---
description: 安装/更新 zcode-hud（主题 + 动画状态条，修改 app.asar，重启客户端生效）
---
把主题与动画状态条安装到本机 ZCode 桌面客户端。整套实现只有一次 app.asar 注入：wrapper loader 注入主题 CSS 并链式加载 vendored 原版状态条（触发式本地查询进程，空闲零轮询）。

执行步骤（插件根目录 = 本命令文件所在目录的上一级）：

1. 部署运行时资产（不需要 root）：

    python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" deploy

2. 查看状态：

    python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" status

3. 如果状态显示「补丁 marker: 无」，打补丁（resources 目录可写时免授权）：

    python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" patch

   若提示目录不可写，改用系统授权（会弹出授权框，输入登录密码）：

    pkexec python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" patch --home "$HOME"

若 `${ZCODE_PLUGIN_ROOT}` 为空，先用 `find ~/.zcode/cli/plugins/cache -maxdepth 4 -type d -name zcode-hud | tail -1` 定位插件根目录。

结果处理：

- 成功：告知用户「✅ 已注入；请完全退出 ZCode（不是关窗口）再重新打开」。
- 已是「已包含注入」：只需重启客户端即可。
- 脚本报「当前 asar 含其它补丁」：说明 asar 被其它工具改过，先恢复原版（重装 ZCode 或用对应工具的卸载功能），再重跑本命令。
- 磁盘空间不足：把脚本输出的需求/可用值原样转述。

用户附加要求：$ARGUMENTS
