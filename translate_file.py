#!/usr/bin/env python3
"""Simplest test of the free Index-Translate online API (Option 1, zero GPU, zero deps).

Text -> text, and file -> text. Images are sent to the model's vision encoder (no OCR).

Usage:
    python3 translate_file.py                              # built-in simplest words
    python3 translate_file.py "你好" --target en            # one phrase
    python3 translate_file.py notes.txt                    # text file  -> printed
    python3 translate_file.py notes.txt -o out.txt         # text file  -> saved
    python3 translate_file.py screenshot.png               # image file -> printed
    python3 translate_file.py Chinese.txt --target en -m Index-Translate-9B
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://index-translate.bilibili.com/v1/chat/completions"
DEFAULT_MODEL = "Index-Translate-35B-A3B"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
# The public gateway cuts requests off at ~30s, so keep chunks small enough that
# one response finishes in time (~2k source chars takes ~15s on 35B-A3B).
CHUNK_CHARS = 1500


def _post(payload, timeout=120, retries=3):
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Index-Translate-Client/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
            return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            err = f"HTTP {e.code}: {detail}"
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise SystemExit(err)
        except (urllib.error.URLError, TimeoutError) as e:
            err = f"network: {e}"
            if attempt == retries:
                raise SystemExit(err)
        print(f"  retry {attempt}/{retries - 1} ({err})", file=sys.stderr)
        time.sleep(2 * attempt)
    raise SystemExit(err)


def translate(text, target="en", model=DEFAULT_MODEL):
    prompt = (
        f"请将以下文本翻译为{target}，直接输出翻译结果，要搞笑一点，不要进行任何解释。\n\n{text}"
    )
    return _post(
        {"model": model, "messages": [{"role": "user", "content": prompt}]}
    )


def translate_image(path, target="en", model=DEFAULT_MODEL):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    content = [
        {
            "type": "text",
            "text": f"Translate the text in the image into {target}. "
                    f"Output only the translation, no explanation.",
        },
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    ]
    return _post(
        {"model": model, "messages": [{"role": "user", "content": content}]}
    )


def split_chunks(text, limit=CHUNK_CHARS):
    """Split on blank lines / sentence ends so no sentence is cut in half."""
    chunks, buf = [], ""
    for para in text.splitlines(keepends=True):
        if len(buf) + len(para) > limit and buf:
            chunks.append(buf)
            buf = ""
        buf += para
    if buf:
        chunks.append(buf)
    return chunks


def translate_text(text, target="en", model=DEFAULT_MODEL):
    parts = split_chunks(text)
    if len(parts) == 1:
        return translate(text, target, model)
    out = []
    for i, part in enumerate(parts, 1):
        print(f"[{i}/{len(parts)}] translating {len(part)} chars...", file=sys.stderr)
        out.append(translate(part, target, model))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="text, or path to a .txt/.md/.srt/.../image file")
    ap.add_argument("--target", "-t", default="en", help="target language, default en")
    ap.add_argument("--model", "-m", default=DEFAULT_MODEL)
    ap.add_argument("--output", "-o", help="write result to this file instead of stdout")
    args = ap.parse_args()

    if not args.input:
        for w in ["你好", "猫", "水", "朋友", "谢谢"]:
            print(f"{w}  ->  {translate(w, args.target, args.model)}")
        return

    if os.path.isfile(args.input):
        ext = os.path.splitext(args.input)[1].lower()
        if ext in IMAGE_EXT:
            result = translate_image(args.input, args.target, args.model)
        else:
            with open(args.input, encoding="utf-8") as f:
                result = translate_text(f.read(), args.target, args.model)
    else:
        result = translate(args.input, args.target, args.model)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(f"written: {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
