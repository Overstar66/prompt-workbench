# -*- coding: utf-8 -*-
"""前后对比：用旧词库（backup_wd14_pre）重算同一批图片的「中文命中率」。"""
import json, sys, uuid, urllib.request

OLD = json.load(open(r"D:\提示词生成\studio2\tags_cn.backup_wd14_pre.json", encoding="utf-8"))["tags"]
old_map = {(e.get("en") or "").strip(): (e.get("zh") or "").strip() for e in OLD}

IMGS = ["anime_style", "3d", "cyberpunk", "greyscale", "cinematic_lighting", "chibi"]


def post(path):
    data = open(path, "rb").read()
    b = "----dsh" + uuid.uuid4().hex
    body = b"".join([
        ("--%s\r\n" % b).encode(),
        b'Content-Disposition: form-data; name="image"; filename="t.jpg"\r\n',
        b"Content-Type: image/jpeg\r\n\r\n", data, ("\r\n--%s--\r\n" % b).encode()])
    req = urllib.request.Request("http://127.0.0.1:8901/api/reverse_upload?polish=0", data=body,
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


tot = tb = ta = 0
for name in IMGS:
    res = post(r"D:\提示词生成\studio2\styles\%s.jpg" % name)
    tags = res.get("tags") or []
    n = len(tags)
    before = sum(1 for t in tags if old_map.get(t["en"]) and old_map[t["en"]] != t["en"])
    after = sum(1 for t in tags if t.get("zh") and t["zh"] != t["en"])
    tot += n; tb += before; ta += after
    print("%-20s tags=%2d  before=%2d (%5.1f%%)  after=%2d (%5.1f%%)"
          % (name, n, before, 100.0*before/max(1,n), after, 100.0*after/max(1,n)))
print("-" * 70)
print("合计 %d tags：before %d (%.1f%%) → after %d (%.1f%%)"
      % (tot, tb, 100.0*tb/max(1,tot), ta, 100.0*ta/max(1,tot)))
