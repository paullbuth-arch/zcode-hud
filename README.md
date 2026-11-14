# dev-personal-plugins

turing 的个人 ZCode 插件市场。

| 插件 | 说明 |
|---|---|
| [zcode-hud](zcode-hud/) | ZCode 桌面主题（壁纸 + 玻璃表面 + JetBrains Mono）+ 原版动画状态条（vendored zusage v1.5.19），单次 asar 注入 |

## 安装

ZCode → 设置 → 插件 → 添加插件市场：

- GitHub：`paullbuth-arch/zcode-hud`（私有仓库，需本机 gh/git 已登录）
- 或本地路径：`/home/turing/software/personal-contents/plugins`

安装插件后在对话框运行 `/install`，然后**完全退出 ZCode 再重新打开**。

## 维护

- 插件源码在 `zcode-hud/`；改动后 commit + push，在 ZCode 插件页更新（或重跑 `/install` 重新部署运行时）。
- ZCode 客户端升级会覆盖 asar 注入，重跑 `/install` 即可。
- 状态条上游同步步骤见 [zcode-hud/vendor/UPSTREAM.md](zcode-hud/vendor/UPSTREAM.md)。

## 许可

MIT（含 vendored 上游代码，见 `LICENSE` 与 `zcode-hud/vendor/zusage/LICENSE`）。
JetBrains Mono 字体遵循 SIL OFL 1.1（见 `zcode-hud/theme/fonts/OFL.txt`）。