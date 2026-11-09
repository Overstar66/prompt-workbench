# -*- coding: utf-8 -*-
"""验证 8901 图反推：上传测试图，统计 tags 里 zh != en 的比例。"""
import json, os, sys, urllib.request
import uuid

IMG = sys.argv[1] if len(sys.argv) > 1 else r"D:\提示词生成\studio\styles\anime_style.jpg"
URL = "http://127.0.0.1:8901/api/reverse_upload?polish=0"


def post(path):
    data = open(path, "rb").read()
    b = "----dsh" + uuid.uuid4().hex
    body = b"".join([
        ("--%s\r\n" % b).encode(),
        b'Content-Disposition: form-data; name="image"; filename="test.jpg"\r\n',
        b"Content-Type: image/jpeg\r\n\r\n",
        data,
        ("\r\n--%s--\r\n" % b).encode(),
    ])
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


if not os.path.isfile(IMG):
    print("MISSING IMAGE", IMG)
    sys.exit(1)
res = post(IMG)
tags = res.get("tags") or []
zh_ok = sum(1 for t in tags if t.get("zh") and t["zh"] != t["en"])
print("image:", IMG)
print("tags: %d, zh != en: %d (%.1f%%)" % (len(tags), zh_ok, 100.0 * zh_ok / max(1, len(tags))))
print("text:", (res.get("text") or "")[:400])
for t in tags:
    flag = "" if (t.get("zh") and t["zh"] != t["en"]) else "   <== EN"
    print("  %-34s %-24s%s" % (t.get("en"), t.get("zh"), flag))
