# -*- coding: utf-8 -*-
"""验证「自动补场景」+「英文锚点已删除」：用 Playwright 驱动本机 Chrome 跑真实页面。

1) 只选一个非场景标签 + 勾选自动补场景 → MOSS 出现「场景：…」
2) 取消勾选 → 同一组标签 MOSS 不再出现「场景：…」
3) 勾选状态写进 localStorage.settings.autoScene，刷新后保持
4) 顶部「英文锚点」开关（#swEn）已从界面删除

用法：python verify_autoscene.py
"""
import sys

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8901"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WAIT_LIB = ("() => { const el = document.querySelector('#libCount');"
            " return el && !el.innerText.includes('加载中'); }")
WAIT_MOSS = ("() => document.querySelector('#resBody').innerText.includes('MOSS 中文')")


def moss_once(pg):
    pg.click("#btnClearRes")
    pg.click("#btnMoss")
    pg.wait_for_function(WAIT_MOSS, timeout=90000)
    return pg.locator("#resBody").inner_text()


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, executable_path=CHROME)
        pg = b.new_page()
        pg.goto(URL, wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_function(WAIT_LIB, timeout=30000)

        n_en = pg.locator("#swEn").count()
        print("① #swEn（英文锚点）元素数量：%d  %s" % (n_en, "PASS" if n_en == 0 else "FAIL"))
        ok = ok and n_en == 0

        pg.select_option("#selPolish", "off")          # 免等本地润色
        pg.click("#searchBox")
        pg.keyboard.type("微笑")
        pg.wait_for_timeout(600)
        first = pg.locator("#tagList .tag").first
        first.click()                                  # 加一个「外形 / 表情」标签，不是场景
        pg.wait_for_timeout(300)
        print("② 已选数量：%s" % pg.locator("#selCount").inner_text())
        print("   自动补场景默认勾选：%s" % pg.locator("#autoScene").is_checked())

        t1 = moss_once(pg)
        got_scene = "场景：" in t1
        print("③ 勾选 + 无场景标签 → MOSS 出现「场景：…」：%s" % ("PASS" if got_scene else "FAIL"))
        print("   MOSS 预览：%s" % t1.replace("\n", " ")[:160])
        ok = ok and got_scene

        pg.uncheck("#autoScene")
        pg.wait_for_timeout(250)
        t2 = moss_once(pg)
        no_scene = "场景：" not in t2
        print("④ 取消勾选 → MOSS 不含「场景：…」：%s" % ("PASS" if no_scene else "FAIL"))
        print("   MOSS 预览：%s" % t2.replace("\n", " ")[:160])
        ok = ok and no_scene

        st = pg.evaluate("() => JSON.parse(localStorage.getItem('settings') || '{}')")
        saved = st.get("autoScene") is False and "en" not in st
        print("⑤ localStorage.settings：autoScene=%r，残留 en 键=%r  %s"
              % (st.get("autoScene"), "en" in st, "PASS" if saved else "FAIL"))
        ok = ok and saved

        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_function(WAIT_LIB, timeout=30000)
        off_after = pg.locator("#autoScene").is_checked() is False
        print("⑥ 刷新后仍保持「未勾选」：%s" % ("PASS" if off_after else "FAIL"))
        ok = ok and off_after

        pg.check("#autoScene")
        pg.wait_for_timeout(250)
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_function(WAIT_LIB, timeout=30000)
        on_after = pg.locator("#autoScene").is_checked() is True
        print("⑦ 重新勾选后刷新保持「勾选」：%s" % ("PASS" if on_after else "FAIL"))
        ok = ok and on_after

        # ⑧ 「生成结果」（doGenerate）也走同一套自动补场景
        pg.select_option("#selPolish", "off")
        pg.click("#searchBox")
        pg.keyboard.type("微笑")
        pg.wait_for_timeout(600)
        pg.locator("#tagList .tag").first.click()
        pg.wait_for_timeout(300)
        pg.click("#btnClearRes")
        pg.click("#btnGen")
        pg.wait_for_function(
            "() => document.querySelector('#resBody').innerText.includes('WAI / NoobAI')", timeout=120000)
        t3 = pg.locator("#resBody").inner_text()
        gen_ok = "场景：" in t3
        print("⑧ 「生成结果」也自动补场景：%s" % ("PASS" if gen_ok else "FAIL"))
        print("   MOSS 预览：%s" % t3.replace("\n", " ")[:120])
        ok = ok and gen_ok
        b.close()
    print("\n结果：", "全部 PASS" if ok else "有 FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
