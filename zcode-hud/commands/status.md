---
description: 只读检查 zcode-hud 的补丁、运行时资产和壁纸状态
---
检查 zcode-hud 的安装状态（只读，不修改任何文件）。

    python3 "${ZCODE_PLUGIN_ROOT}/scripts/install.py" status

若 `${ZCODE_PLUGIN_ROOT}` 为空，先用 `find ~/.zcode/cli/plugins/cache -maxdepth 4 -type d -name zcode-hud | tail -1` 定位插件根目录。

把输出整理成简表转述，并保留最后一行的「结论」。根据结论给一句下一步建议（无需操作 / 运行 /install / 先执行 unpatch 或重装 ZCode）。

用户附加要求：$ARGUMENTS
