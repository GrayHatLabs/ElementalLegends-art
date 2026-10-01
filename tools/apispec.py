"""Print request/response schemas for PixelLab endpoints: python apispec.py /path ..."""
import json
import sys
from pathlib import Path

spec = json.loads(Path(__file__).with_name("openapi.json").read_text(encoding="utf-8-sig"))
C = spec["components"]["schemas"]


def res(x):
    if isinstance(x, dict) and "$ref" in x:
        return C[x["$ref"].split("/")[-1]]
    return x


def brief(v):
    v = res(v)
    if "anyOf" in v:
        opts = [res(a).get("title") or res(a).get("type") for a in v["anyOf"]]
        return {"anyOf": opts, "default": v.get("default"), "description": v.get("description")}
    keys = ("type", "default", "enum", "minimum", "maximum", "description", "title")
    return {k: v.get(k) for k in keys if v.get(k) is not None}


def show(path):
    ops = spec["paths"][path]
    for method, op in ops.items():
        print("=====", method.upper(), path)
        print((op.get("description") or "")[: 100000 if FULL else 700])
        rb = op.get("requestBody")
        if rb:
            sc = res(list(rb["content"].values())[0]["schema"])
            req = sc.get("required", [])
            for k, v in sc.get("properties", {}).items():
                print("  " + ("*" if k in req else " "), k, json.dumps(brief(v))[:300])
        for code, r in op.get("responses", {}).items():
            if code.startswith("2") and r.get("content"):
                sc = res(list(r["content"].values())[0]["schema"])
                print("  ->", code, {k: brief(v).get("type") or brief(v).get("anyOf") for k, v in sc.get("properties", {}).items()})


FULL = "--full" in sys.argv
for p in sys.argv[1:]:
    if p != "--full":
        show(p)
