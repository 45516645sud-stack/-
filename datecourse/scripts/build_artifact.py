#!/usr/bin/env python3
"""index.html 을 claude.ai 아티팩트로 올릴 수 있는 모양으로 바꾼다.

    python scripts/build_artifact.py <출력 폴더>

아티팩트는 문서 뼈대를 직접 씌우고, 외부 CSS·서비스 워커·Web Share·#key=value 주소를 막는다.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def must(s: str, old: str, new: str) -> str:
    assert old in s, old[:70]
    return s.replace(old, new)


def build(s: str) -> str:
    for pat in [r'<!doctype html>\n', r'<html lang="ko">\n', r'<head>\n', r'</head>\n', r'<body>\n', r'</body>\n',
                r'</html>\n', r'<meta charset="utf-8">\n', r'<meta name="viewport"[^>]*>\n',
                r'<meta name="theme-color"[^>]*>\n', r'<link rel="manifest"[^>]*>\n', r'<link rel="icon"[^>]*>\n',
                r'<link rel="stylesheet"[^>]*>\n', r'<script src="https://cdnjs[^>]*></script>\n']:
        s, n = re.subn(pat, '', s)
        assert n, pat
    s = s.replace('<style>', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap">\n<style>', 1)
    s = must(s, '--font: "Pretendard Variable", Pretendard,', '--font: "Noto Sans KR",')
    s = must(s, '.appbar { position: sticky; top: 0;', '.appbar { position: sticky; top: env(safe-area-inset-top, 0px);')
    # 아티팩트 링크는 #코스id 하나만 넘긴다
    s = must(s, '''  const url = location.href.split("#")[0] + "#c=" + encodeURIComponent(c.id);\n''', '')
    s = s.replace('"#c=" + encodeURIComponent', '"#" + encodeURIComponent')
    s = must(s, 'const m = location.hash.match(/^#c=(.+)$/);', 'const m = location.hash.match(/^#([\\w.~-]+)$/);')
    # Web Share·prompt 는 막혀 있고 주소도 아티팩트 링크가 아니라서, 코스 순서만 복사한다
    s = must(s, '''  try {
    if (navigator.share) { await navigator.share({ title: c.title, text, url }); return; }
  } catch (e) { if (e && e.name === "AbortError") return; }
''', '')
    s = must(s, '''    await navigator.clipboard.writeText(text + "\\n" + url);
    toast("코스 링크를 복사했어요");''', '''    await navigator.clipboard.writeText(text);
    toast("코스 순서를 복사했어요");''')
    s = must(s, 'prompt("이 주소를 복사하세요", url);', 'toast("복사하지 못했어요. 코스 이름으로 검색해 보세요");')
    s = must(s, '<button class="btn" id="shareBtn">${icon("copy")}공유</button>', '<button class="btn" id="shareBtn">${icon("copy")}복사</button>')
    s, n = re.subn(r'\nif \("serviceWorker" in navigator.*?\n}\n', '\n', s, flags=re.S)
    assert n
    return s


if __name__ == "__main__":
    out = Path(sys.argv[1])
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(build((ROOT / "index.html").read_text(encoding="utf-8")), encoding="utf-8")
    shutil.copy(ROOT / "data" / "courses.json", out / "data" / "courses.json")
    print("ok", out)
