#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量翻译 Sphinx 项目的 .po 文件到多种语言。
支持递归处理深层 .po 文件，带进度显示和超时控制。
"""

import sys
import time
from pathlib import Path

# ========== 用户配置 ==========
LANGUAGES = ['ja', 'zh_CN', 'zh_TW', 'ko', 'ru']
SOURCE_LANG = 'en'
REQUEST_DELAY = 0.8          # 每条翻译间隔（秒），防限流
REQUEST_TIMEOUT = 30         # 单条请求超时（秒）
MAX_RETRIES = 3              # 单条翻译失败重试次数
ENABLE_TRANSLATION = True

LANG_MAP = {
    'zh_CN': 'zh-CN',
    'zh_TW': 'zh-TW',
}
# ================================

try:
    import polib
    from deep_translator import GoogleTranslator
except ImportError:
    print("❌ 请安装依赖: pip install polib deep-translator")
    sys.exit(1)


def find_locale_dir(start_path: Path) -> Path:
    current = start_path.resolve()
    for _ in range(10):
        candidate = current / 'locale'
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def translate_po_file(po_path: Path, target_lang: str, locale_dir: Path):
    """翻译单个 .po 文件，带进度显示"""
    rel_path = po_path.relative_to(locale_dir)
    print(f"\n  📄 {rel_path}")

    po = polib.pofile(str(po_path))
    target_code = LANG_MAP.get(target_lang, target_lang)

    empty_entries = [e for e in po if e.msgstr == "" and e.msgid]
    total = len(empty_entries)

    if total == 0:
        print("     ✅ 无需翻译（所有条目已有译文）")
        return

    print(f"     📝 待翻译: {total} 条")

    translated = 0
    for idx, entry in enumerate(empty_entries, 1):
        # 每 5 条或每 50 条显示一次进度
        if idx % 5 == 0 or idx == 1 or idx == total:
            print(f"     ⏳ 进度: {idx}/{total} ({idx*100//total}%) - {entry.msgid[:40]}...")

        # 带重试的翻译
        for attempt in range(MAX_RETRIES):
            try:
                translator = GoogleTranslator(
                    source=SOURCE_LANG,
                    target=target_code,
                    timeout=REQUEST_TIMEOUT
                )
                entry.msgstr = translator.translate(entry.msgid)
                translated += 1
                time.sleep(REQUEST_DELAY)
                break  # 成功则跳出重试循环
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"     ⚠️ 重试 {attempt+1}/{MAX_RETRIES}: {entry.msgid[:30]}...")
                    time.sleep(2)  # 重试前等待 2 秒
                else:
                    print(f"     ❌ 翻译失败: {entry.msgid[:40]}... → {e}")
                continue

    if translated:
        backup = po_path.with_suffix(po_path.suffix + '.bak')
        po_path.rename(backup)
        po.save(str(po_path))
        print(f"     ✅ 完成: {translated}/{total} 条，备份: {backup.name}")
    else:
        print("     ⚠️ 未新增任何翻译")


def main():
    script_dir = Path(__file__).parent
    locale_dir = find_locale_dir(script_dir)

    if not locale_dir:
        print("❌ 未找到 locale/ 目录")
        sys.exit(1)

    print(f"✅ 找到 locale 目录: {locale_dir}")

    if not ENABLE_TRANSLATION:
        print("ℹ️ 翻译功能已关闭，仅扫描文件...")
        for lang in LANGUAGES:
            lang_path = locale_dir / lang / 'LC_MESSAGES'
            if lang_path.exists():
                po_files = list(lang_path.rglob('*.po'))
                print(f"  {lang}: {len(po_files)} 个 .po 文件")
        return

    for lang in LANGUAGES:
        lang_dir = locale_dir / lang / 'LC_MESSAGES'
        if not lang_dir.is_dir():
            print(f"⚠️ 跳过 {lang}：目录不存在")
            continue

        po_files = list(lang_dir.rglob('*.po'))
        if not po_files:
            print(f"⚠️ 跳过 {lang}：没有 .po 文件")
            continue

        print(f"\n🌐 处理语言: {lang} ({len(po_files)} 个文件)")
        for po_file in po_files:
            translate_po_file(po_file, lang, locale_dir)

    print("\n✅ 所有翻译任务完成！")
    print("📌 请运行: sphinx-intl build")


if __name__ == '__main__':
    main()

