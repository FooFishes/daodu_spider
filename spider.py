#!/usr/bin/env python3
"""雨课堂课件图片爬虫 - 过滤习题"""

import os
import re
import sys
import requests
from playwright.sync_api import sync_playwright


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


def download_image(url: str, save_path: str) -> bool:
    """下载图片到指定路径"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"下载失败: {url}\n错误: {e}")
        return False


def get_slide_images(frame):
    """从 frame 中获取所有课件图片 URL"""
    imgs = frame.query_selector_all('img[data-src]')
    urls = []
    for img in imgs:
        data_src = img.get_attribute('data-src')
        if data_src and 'slide' in data_src:
            urls.append(data_src)
    return urls


def find_content_frame(page):
    """找到包含课件的 iframe"""
    for frame in page.frames:
        if '/m/v2/lesson/student/' in frame.url:
            return frame
    return None


def main():
    if len(sys.argv) < 2:
        print("用法: python spider.py <课程URL>")
        print("例如: python spider.py https://changjiang.yuketang.cn/v2/web/student-lesson-report/...")
        sys.exit(1)

    url = sys.argv[1]
    login_url = "https://changjiang.yuketang.cn/web"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 登录
        print(f"正在打开登录页: {login_url}")
        page.goto(login_url)
        print("\n请在浏览器中完成登录后按回车...")
        input()

        # 跳转到课程页
        print(f"\n正在跳转到课程页面: {url}")
        page.goto(url)
        print("等待页面加载...")
        page.wait_for_selector('.lesson-title', timeout=60000)

        # 获取标题
        lesson_title = page.query_selector('.lesson-title').inner_text().strip()
        lesson_title = sanitize_filename(lesson_title)
        print(f"课程标题: {lesson_title}")

        # 等待 iframe 加载
        page.wait_for_timeout(2000)

        # 找到内容 iframe
        content_frame = find_content_frame(page)
        if not content_frame:
            print("未找到内容 iframe")
            browser.close()
            sys.exit(1)

        # 点击「课件」Tab（在 iframe 中）
        print("\n正在点击「课件」Tab...")
        tabs = content_frame.query_selector_all('.tab-item')
        for tab in tabs:
            if '课件' in tab.inner_text():
                tab.click()
                break

        # 等待加载
        print("等待课件加载...")
        page.wait_for_timeout(5000)

        # 获取「全部」图片
        print("\n获取「全部」图片列表...")
        all_imgs = get_slide_images(content_frame)
        print(f"  全部图片: {len(all_imgs)} 张")

        # 点击「习题」Tab
        print("\n正在切换到「习题」Tab...")
        sub_tabs = content_frame.query_selector_all('.tab-wrap .tab-item')
        for tab in sub_tabs:
            text = tab.inner_text().strip()
            if text == '习题':
                tab.click()
                break

        # 等待加载
        page.wait_for_timeout(2000)

        # 获取「习题」图片
        exercise_imgs = get_slide_images(content_frame)
        print(f"  习题图片: {len(exercise_imgs)} 张")

        # 计算差集（全部 - 习题）
        exercise_set = set(exercise_imgs)
        final_imgs = [img for img in all_imgs if img not in exercise_set]
        print(f"\n最终保留: {len(final_imgs)} 张非习题图片")

        # 关闭浏览器
        browser.close()

        if not final_imgs:
            print("未找到图片")
            sys.exit(1)

        # 创建保存目录
        save_dir = os.path.join(os.getcwd(), lesson_title)
        os.makedirs(save_dir, exist_ok=True)
        print(f"保存目录: {save_dir}")

        # 下载图片
        print("\n开始下载图片...")
        for i, img_url in enumerate(final_imgs, 1):
            filename = f"{lesson_title}_{i:03d}.jpg"
            save_path = os.path.join(save_dir, filename)
            print(f"[{i}/{len(final_imgs)}] 下载: {filename}")
            if download_image(img_url, save_path):
                print(f"  ✓ 完成")
            else:
                print(f"  ✗ 失败")

        print(f"\n下载完成！图片保存在: {save_dir}")


if __name__ == '__main__':
    main()
