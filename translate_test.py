#!/usr/bin/env python3
"""Simplest test of the free Index-Translate online API (Option 1, zero GPU, zero deps).

Usage:
    python3 translate_test.py                 # built-in simplest words
    python3 translate_test.py 你好 --target en
"""
import json
import sys
import urllib.request

API_URL = "https://index-translate.bilibili.com/v1/chat/completions"
MODEL = "Index-Translate-35B-A3B"


def translate(text, target="en", source="auto", model=MODEL):
    prompt = (
        f"请将以下文本翻译为{'英语' if target == 'en' else target}，"
        f"直接输出翻译结果，不要进行任何解释。\n\n{text}"
    )
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Index-Translate-Client/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
        target = sys.argv[3] if len(sys.argv) > 2 and sys.argv[2] == "--target" else "en"
        print(f"{text}  ->  {translate(text, target)}")
    else:
        words = ["你好", "猫", "水", "朋友", "谢谢"]  # simplest words
        for w in words:
            print(f"{w}  ->  {translate(w)}")
