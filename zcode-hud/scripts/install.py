#!/usr/bin/env python3
"""zcode-hud installer / uninstaller / status.

Subcommands:
    deploy     copy runtime assets, fonts, theme CSS, vendored statusbar and sync wallpaper (user)
    patch      apply the single asar injection (needs write access to app.asar)
    unpatch    restore the pristine app.asar from the backup (needs write access)
    install    deploy + patch
    status     read-only report

The app.asar patch is one appended dynamic import in out/main/index.js; the
theme CSS and the vendored zusage statusbar are loaded by that loader at
runtime, so there is no second patch point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asar_patch import entry_bytes, repack  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = PLUGIN_ROOT / "runtime"
THEME_SRC = PLUGIN_ROOT / "theme"
VENDOR_SRC = PLUGIN_ROOT / "vendor" / "zusage"

# Written once on first deploy; the overlay's settings panel edits this file
# at runtime, so later deploys must not clobber the user's toggles.
ZUSAGE_CONFIG_DEFAULTS = {
    "resident": True,
    "python_path": "python3",
    "quota_enabled": False,          # no credential decryption / quota queries
    "reset_badge_enabled": False,    # same, for the reset-card badge
    "plugin_auto_update": False,     # updates are maintained in this repo
    "auto_compact_patch": False,     # never touch the agent engine
    "answer_rate_line": True,
    "enhance_enabled": True,
    "restart_notice": True,
}

ENTRY = "out/main/index.js"
MARKER = b"[zcode-hud]"
ASAR_CANDIDATES = (
    "/opt/ZCode/resources/app.asar",
    "/opt/zcode/resources/app.asar",
    "/usr/lib/zcode/resources/app.asar",
    "/usr/local/ZCode/resources/app.asar",
)
THEME_STATE = ".zcode/theme-maintenance/state.json"


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> "None":
    log(f"[!] {msg}")
    raise SystemExit(code)


def resolve_home(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    uid = os.environ.get("PKEXEC_UID")
    if uid:
        try:
            return Path(pwd.getpwuid(int(uid)).pw_dir)
        except KeyError:
            pass
    return Path.home()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_asar(override: str | None) -> Path:
    if override:
        path = Path(override)
        if not path.exists():
            fail(f"app.asar not found: {path}")
        return path
    for candidate in ASAR_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    fail("cannot locate ZCode app.asar; pass --asar")


def inject_line(runtime_dir: Path) -> bytes:
    url = (runtime_dir / "inject-main.cjs").as_uri()
    return (
        f'\n;import("{url}").then(() => null, '
        f'(e) => console.error("[zcode-hud] load failed", e));'
    ).encode()


def asar_version(asar: Path) -> str | None:
    try:
        return json.loads(entry_bytes(asar, "package.json")).get("version")
    except Exception:
        return None


def has_marker(asar: Path) -> bool:
    try:
        return MARKER in entry_bytes(asar, ENTRY)
    except Exception:
        return False


def has_foreign_patch(asar: Path) -> bool:
    try:
        if b"zusage" in entry_bytes(asar, ENTRY):
            return True
        if b"wez.css" in entry_bytes(asar, "out/renderer/index.html"):
            return True
    except Exception:
        pass
    return False


def seed_backup_from_theme(home: Path, asar: Path, backup: Path) -> bool:
    """Migrate the pristine asar recorded by the old zcode-theme plugin."""
    state_path = home / THEME_STATE
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        original = Path(state["backup"])
        current = sha256(asar)
        if current != state.get("patched_sha256"):
            return False
        if sha256(original) != state.get("original_sha256"):
            return False
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, backup)
        log(f"[+] 已从旧主题备份迁移 pristine asar: {original}")
        return True
    except Exception as exc:
        log(f"[!] 迁移旧主题备份失败: {exc}")
        return False


def deploy(home: Path) -> None:
    ui = home / ".zcode-ui"
    hud = ui / "hud"
    fonts = ui / "fonts"
    zusage = ui / "zusage"
    hud.mkdir(parents=True, exist_ok=True)
    fonts.mkdir(parents=True, exist_ok=True)

    shutil.copy2(RUNTIME_SRC / "inject-main.cjs", hud / "inject-main.cjs")

    css = (THEME_SRC / "wez.css").read_text(encoding="utf-8")
    css = css.replace("__HOME__", str(home))
    (hud / "theme.css").write_text(css, encoding="utf-8")

    for font in sorted((THEME_SRC / "fonts").glob("*.ttf")):
        shutil.copy2(font, fonts / font.name)

    # Vendored statusbar: overwrite code files, keep runtime-generated files
    # (config.json, caches) so user toggles and pricing data survive redeploys.
    shutil.copytree(VENDOR_SRC, zusage, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    cfg = zusage / "config.json"
    if not cfg.exists():
        cfg.write_text(json.dumps(ZUSAGE_CONFIG_DEFAULTS, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        log(f"[+] 状态条默认配置已写入（额度查询/自动更新已关）: {cfg}")

    sync_wallpaper(home)
    log(f"[+] 运行时已部署: {hud} + {zusage}")


def sync_wallpaper(home: Path) -> None:
    target = home / ".zcode" / "v2" / "wall.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    source = None
    try:
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip().strip("'")
        if out.startswith("file://"):
            candidate = Path(out[len("file://"):])
            if candidate.exists():
                source = candidate
    except Exception:
        pass
    if source is None:
        candidate = home / ".config" / "background"
        if candidate.exists():
            source = candidate
    if source is None:
        log("[!] 未找到桌面壁纸，保留现有 wall.png")
        return
    if not target.exists() or sha256(source) != sha256(target):
        shutil.copy2(source, target)
        log(f"[+] 壁纸已同步: {source} -> {target}")


def patch(home: Path, asar_path: str | None) -> None:
    asar = find_asar(asar_path)
    hud = home / ".zcode-ui" / "hud"
    if not (hud / "inject-main.cjs").exists():
        fail("运行时尚未部署，先运行 deploy")
    # Atomic replace only needs write access to the containing directory;
    # the asar file itself may stay root-owned (e.g. after an RPM upgrade).
    if not os.access(asar.parent, os.W_OK) and os.geteuid() != 0:
        fail("app.asar 所在目录不可写；请用 pkexec 运行 patch（或先修复目录属主）")
    if has_marker(asar):
        log("[=] app.asar 已包含 zcode-hud 注入，无需重复打补丁")
        return

    backup = home / ".zcode-ui" / "backups" / "app.asar.original"
    version = asar_version(asar)

    if backup.exists():
        base_version = asar_version(backup)
        if base_version != version:
            if has_foreign_patch(asar):
                fail(
                    f"备份版本 {base_version} 与当前客户端 {version} 不一致，"
                    "且当前 asar 已有其它补丁；请先恢复原版（/uninstall-theme 或重装 ZCode）"
                )
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asar, backup)
            log(f"[+] 客户端版本变化，已重建 pristine 备份 ({version})")
    else:
        if has_foreign_patch(asar):
            if seed_backup_from_theme(home, asar, backup):
                pass
            else:
                fail(
                    "当前 app.asar 含其它补丁（zusage 或旧主题），且找不到可用的 pristine 备份；"
                    "请先运行 /uninstall-theme 或重装 ZCode"
                )
        else:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asar, backup)
            log(f"[+] 已创建 pristine 备份: {backup}")

    line = inject_line(hud)
    entry = entry_bytes(backup, ENTRY)
    if MARKER in entry:
        entry = entry.replace(line, b"").replace(line.lstrip(b"\n"), b"")
    new_entry = entry + line

    free = shutil.disk_usage(asar.parent).free
    need = backup.stat().st_size + asar.stat().st_size + 64 * 1024 * 1024
    if free < need:
        fail(f"磁盘空间不足：需要约 {need // (1024*1024)} MB，可用 {free // (1024*1024)} MB")

    tmp = asar.with_name(asar.name + ".zhud.tmp")
    log(f"[*] 正在重建 app.asar（{len(new_entry)} byte 入口，约 373MB 拷贝）...")
    repack(backup, {"/" + ENTRY: new_entry}, tmp)

    if MARKER not in entry_bytes(tmp, ENTRY):
        tmp.unlink(missing_ok=True)
        fail("补丁校验失败：写入后找不到 marker")
    if asar_version(tmp) != version:
        tmp.unlink(missing_ok=True)
        fail("补丁校验失败：package.json 版本变化")

    mode = asar.stat().st_mode & 0o7777
    owner = (asar.stat().st_uid, asar.stat().st_gid)
    with open(tmp, "rb") as stream:
        os.fsync(stream.fileno())
    os.replace(tmp, asar)
    os.chmod(asar, mode)
    if os.geteuid() == 0:
        os.chown(asar, owner[0], owner[1])
    write_state(home, version, sha256(backup), sha256(asar))
    log(f"[+] 已注入 {asar}（重启 ZCode 后生效）")


def unpatch(home: Path, asar_path: str | None) -> None:
    asar = find_asar(asar_path)
    backup = home / ".zcode-ui" / "backups" / "app.asar.original"
    if not backup.exists():
        fail("找不到 pristine 备份，无法还原；请重装 ZCode 或使用 RPM 校验")
    if not os.access(asar.parent, os.W_OK) and os.geteuid() != 0:
        fail("app.asar 所在目录不可写；请用 pkexec 运行 unpatch")
    if asar_version(backup) != asar_version(asar):
        fail("备份与当前客户端版本不一致，拒绝还原（可能已升级 ZCode）")
    tmp = asar.with_name(asar.name + ".zhud.restore")
    shutil.copy2(backup, tmp)
    mode = asar.stat().st_mode & 0o7777
    owner = (asar.stat().st_uid, asar.stat().st_gid)
    os.replace(tmp, asar)
    os.chmod(asar, mode)
    if os.geteuid() == 0:
        os.chown(asar, owner[0], owner[1])
    state = home / ".zcode-ui" / "hud-state.json"
    state.unlink(missing_ok=True)
    log(f"[+] 已还原 {asar}")


def write_state(home: Path, version: str | None, original_sha: str, patched_sha: str) -> None:
    state = {
        "version": "0.1.0",
        "zcode_version": version,
        "original_sha256": original_sha,
        "patched_sha256": patched_sha,
        "patched_at": datetime.now(timezone.utc).isoformat(),
        "inject_entry": ENTRY,
    }
    path = home / ".zcode-ui" / "hud-state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def status(home: Path, asar_path: str | None) -> None:
    asar = find_asar(asar_path)
    backup = home / ".zcode-ui" / "backups" / "app.asar.original"
    hud = home / ".zcode-ui" / "hud"
    log("=== zcode-hud 状态 ===")
    log(f"app.asar: {asar}")
    log(f"客户端版本: {asar_version(asar)}")
    log(f"可写: {os.access(asar, os.W_OK)}")
    log(f"补丁 marker: {'有' if has_marker(asar) else '无'}")
    log(f"pristine 备份: {backup if backup.exists() else '缺失'}")
    if backup.exists():
        log(f"备份版本: {asar_version(backup)}")
    for name in ("inject-main.cjs", "theme.css"):
        log(f"运行时 {name}: {'OK' if (hud / name).exists() else '缺失'}")
    zusage = home / ".zcode-ui" / "zusage"
    for name in ("inject-main.cjs", "overlay.js", "turn-stats.js", "zusage.py"):
        log(f"状态条 {name}: {'OK' if (zusage / name).exists() else '缺失'}")
    cfg_path = zusage / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            log(f"状态条配置: 额度查询={cfg.get('quota_enabled', True)} "
                f"自动更新={cfg.get('plugin_auto_update', True)} "
                f"速率行={cfg.get('answer_rate_line', True)}")
        except Exception:
            log("状态条配置: 解析失败")
    else:
        log("状态条配置: 缺失（deploy 时写入默认值）")
    wall = home / ".zcode" / "v2" / "wall.png"
    log(f"壁纸: {'OK' if wall.exists() else '缺失'} ({wall})")
    fonts = home / ".zcode-ui" / "fonts"
    log(f"字体: {len(list(fonts.glob('*.ttf')))} 个")
    if has_marker(asar):
        log("结论: 已安装；重启 ZCode 生效")
    else:
        log("结论: 未安装；运行 deploy + patch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["deploy", "patch", "unpatch", "install", "status", "sync-wallpaper"])
    parser.add_argument("--home")
    parser.add_argument("--asar")
    args = parser.parse_args()

    home = resolve_home(args.home)
    if args.action == "deploy":
        deploy(home)
    elif args.action == "patch":
        patch(home, args.asar)
    elif args.action == "unpatch":
        unpatch(home, args.asar)
    elif args.action == "install":
        deploy(home)
        patch(home, args.asar)
    elif args.action == "status":
        status(home, args.asar)
    elif args.action == "sync-wallpaper":
        sync_wallpaper(home)


if __name__ == "__main__":
    main()
