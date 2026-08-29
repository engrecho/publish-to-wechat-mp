#!/usr/bin/env python3
"""把 themes-local/ 下的本地主题注入到 vendor 镜像里。

幂等：已登记的主题不会重复追加。每次上游 rsync 覆盖后重新跑一遍，
产出始终 = 上游最新版 + 本地主题。
"""
import sys
from pathlib import Path

# 以脚本位置定位（脚本在 4_theme-formator/scripts/ 下），任意 cwd 执行均可
STAGE_DIR = Path(__file__).resolve().parent.parent
ROWS_FILE = STAGE_DIR / "themes-local/theme-index.rows.md"
INDEX_FILE = STAGE_DIR / "vendor/gzh-design/references/theme-index.md"
THEMES_LOCAL_DIR = STAGE_DIR / "themes-local"
REFERENCES_DIR = STAGE_DIR / "vendor/gzh-design/references"


def load_local_rows():
    """读取本地登记行，跳过空行和 # 注释行。"""
    if not ROWS_FILE.exists():
        return []
    rows = []
    for line in ROWS_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        rows.append(s)
    return rows


def inject_index_rows(rows):
    """把登记行幂等插入 theme-index.md 表格末尾。"""
    if not rows:
        return
    if not INDEX_FILE.exists():
        print("⚠ 未找到 theme-index.md，跳过 index 注入", file=sys.stderr)
        return

    lines = INDEX_FILE.read_text(encoding="utf-8").splitlines()

    # 找表格分隔线 |---|
    sep_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|---") or line.strip().startswith("|:---"):
            sep_idx = i
            break
    if sep_idx is None:
        print("⚠ 未找到表格分隔线，跳过 index 注入", file=sys.stderr)
        return

    # 找表格结束：分隔线后第一个不以 | 开头的行（含空行）
    table_end = len(lines)
    for j in range(sep_idx + 1, len(lines)):
        if not lines[j].strip().startswith("|"):
            table_end = j
            break

    existing = lines[sep_idx + 1 : table_end]
    existing_blob = "\n".join(existing)
    added = []
    for row in rows:
        # 用主题名列去重（第一列）
        theme_name = row.split("|")[1].strip() if "|" in row else row
        if theme_name and theme_name in existing_blob:
            continue
        existing.append(row)
        added.append(row)

    if added:
        new_lines = lines[: sep_idx + 1] + existing + lines[table_end:]
        INDEX_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"✓ index 注入 {len(added)} 个本地主题")


def copy_theme_files():
    """拷贝 themes-local/theme-*.md 到 vendor/references/。"""
    if not THEMES_LOCAL_DIR.exists():
        return
    count = 0
    for src in THEMES_LOCAL_DIR.glob("theme-*.md"):
        # 跳过 theme-index.rows.md（它是登记数据，不是主题组件库）
        if src.name == "theme-index.rows.md":
            continue
        dst = REFERENCES_DIR / src.name
        dst.write_bytes(src.read_bytes())
        count += 1
    if count:
        print(f"✓ 拷贝 {count} 个本地主题文件到 references/")


if __name__ == "__main__":
    copy_theme_files()
    rows = load_local_rows()
    inject_index_rows(rows)
    print("本地主题注入完成")
