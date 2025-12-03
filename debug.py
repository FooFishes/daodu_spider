#!/usr/bin/env python3
"""分析 iframe 中的 Tab 结构"""

import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "https://changjiang.yuketang.cn/v2/web/student-lesson-report/22896564/1564131811159565952/29753414"
login_url = "https://changjiang.yuketang.cn/web"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print(f"正在打开登录页: {login_url}")
    page.goto(login_url)

    print("\n请在浏览器中完成登录后按回车...")
    input()

    print(f"\n正在跳转到课程页面: {url}")
    page.goto(url)

    print("等待页面加载...")
    page.wait_for_selector('.lesson-title', timeout=60000)
    print(f"课程标题: {page.query_selector('.lesson-title').inner_text()}")

    # 等待 iframe 加载
    print("\n等待 iframe 加载...")
    page.wait_for_timeout(2000)

    print("\n" + "="*60)
    print("分析各 Frame 中的 Tab 相关元素")
    print("="*60)

    for i, frame in enumerate(page.frames):
        print(f"\n--- Frame[{i}]: {frame.url[:70]}... ---")

        # 查找各种可能的 Tab 选择器
        selectors = [
            '.tab-item',
            '[class*="tab"]',
            'span[class*="tab"]',
            'div[class*="tab"]',
            '.tabs',
            '[role="tab"]',
        ]

        for sel in selectors:
            elements = frame.query_selector_all(sel)
            if elements:
                print(f"\n  选择器 '{sel}' 找到 {len(elements)} 个元素:")
                for j, el in enumerate(elements[:5]):
                    tag = el.evaluate('e => e.tagName')
                    class_name = el.get_attribute('class') or ''
                    text = el.inner_text().strip()[:30]
                    print(f"    [{j}] <{tag}> class=\"{class_name}\" text=\"{text}\"")

    # 尝试在各 frame 中点击课件 Tab
    print("\n" + "="*60)
    print("尝试自动点击课件 Tab")
    print("="*60)

    clicked = False
    for i, frame in enumerate(page.frames):
        # 尝试多种选择器
        for sel in ['.tab-item', 'span[class*="tab"]']:
            tabs = frame.query_selector_all(sel)
            for tab in tabs:
                text = tab.inner_text().strip()
                if '课件' in text:
                    print(f"\n在 Frame[{i}] 找到「课件」Tab，正在点击...")
                    tab.click()
                    clicked = True
                    break
            if clicked:
                break
        if clicked:
            break

    if not clicked:
        print("\n未能自动找到课件 Tab")

    # 等待并检查结果
    print("\n等待 5 秒...")
    page.wait_for_timeout(5000)

    # 检查图片
    total = 0
    for frame in page.frames:
        imgs = frame.query_selector_all('img[data-src]')
        slide_imgs = [img for img in imgs if 'slide' in (img.get_attribute('data-src') or '')]
        if slide_imgs:
            total += len(slide_imgs)
            print(f"\nFrame 找到 {len(slide_imgs)} 张课件图片")

    print(f"\n总计找到 {total} 张课件图片")

    print("\n按回车键关闭...")
    input()
    browser.close()
