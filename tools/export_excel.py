# -*- coding: utf-8 -*-
"""把 tags_cn.json 导出为 Excel（按分类分 sheet）"""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = r"D:\提示词生成\studio2"
SRC = os.path.join(ROOT, "tags_cn.json")
OUT = os.path.join(ROOT, "tags_export.xlsx")

data = json.load(open(SRC, encoding="utf-8"))["tags"]
cats = ["角色", "外形", "服装", "动作", "道具", "场景", "自定义"]

wb = Workbook()
ws0 = wb.active
ws0.title = "汇总"
head_fill = PatternFill("solid", fgColor="4C8BF5")
head_font = Font(color="FFFFFF", bold=True)

# 汇总
ws0.append(["分类", "条数", "其中 NSFW"])
for c in ws0[1]:
    c.fill = head_fill; c.font = head_font
for cat in cats:
    rows = [e for e in data if e.get("cat") == cat]
    ws0.append([cat, len(rows), sum(1 for e in rows if e.get("nsfw"))])
ws0.append(["合计", len(data), sum(1 for e in data if e.get("nsfw"))])
ws0.column_dimensions["A"].width = 12
ws0.column_dimensions["B"].width = 10
ws0.column_dimensions["C"].width = 12

# 分类 sheet
for cat in cats:
    rows = [e for e in data if e.get("cat") == cat]
    if not rows:
        continue
    ws = wb.create_sheet(cat)
    is_char = (cat == "角色")
    header = ["中文", "英文", "子类/作品", "NSFW"]
    if is_char:
        header += ["发色", "眼睛", "服装", "体型", "胸围"]
    ws.append(header)
    for c in ws[1]:
        c.fill = head_fill; c.font = head_font
        c.alignment = Alignment(horizontal="center")
    for e in rows:
        row = [e.get("zh", ""), e.get("en", ""), e.get("sub", ""), "是" if e.get("nsfw") else ""]
        if is_char:
            app = e.get("app") or {}
            row += [app.get("hair", ""), app.get("eyes", ""), app.get("outfit", ""),
                    app.get("body", ""), app.get("chest", "")]
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:%s1" % get_column_letter(len(header))
    widths = [16, 26, 16, 6] + ([18] * 5 if is_char else [])
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

wb.save(OUT)
print("已导出:", OUT)
print("大小: %.2f MB" % (os.path.getsize(OUT) / 1048576))
print("sheet:", wb.sheetnames)
