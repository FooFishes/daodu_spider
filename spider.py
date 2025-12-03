#!/usr/bin/env python3
"""雨课堂课件图片爬虫 - 批量下载 + 多线程"""

import os
import re
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


def download_image(args):
    """下载单张图片"""
    url, save_path, index, total = args
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return (index, True, os.path.basename(save_path))
    except Exception as e:
        return (index, False, str(e))


def download_images_parallel(img_urls, save_dir, lesson_title, max_workers=8):
    """多线程下载图片"""
    tasks = []
    for i, img_url in enumerate(img_urls, 1):
        filename = f"{lesson_title}_{i:03d}.jpg"
        save_path = os.path.join(save_dir, filename)
        tasks.append((img_url, save_path, i, len(img_urls)))

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_image, task): task for task in tasks}
        for future in as_completed(futures):
            index, success, info = future.result()
            if success:
                success_count += 1
                print(f"  ✓ [{index}/{len(img_urls)}] {info}")
            else:
                fail_count += 1
                print(f"  ✗ [{index}/{len(img_urls)}] 失败: {info}")

    return success_count, fail_count


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


def process_single_url(page, url):
    """处理单个课程 URL，返回 (标题, 图片列表)"""
    print(f"\n{'='*60}")
    print(f"正在处理: {url}")
    print('='*60)

    page.goto(url)
    page.wait_for_selector('.lesson-title', timeout=60000)

    # 获取标题
    lesson_title = page.query_selector('.lesson-title').inner_text().strip()
    lesson_title = sanitize_filename(lesson_title)
    print(f"课程标题: {lesson_title}")

    # 等待 iframe 加载
    page.wait_for_timeout(2000)

    content_frame = find_content_frame(page)
    if not content_frame:
        print("  ✗ 未找到内容 iframe")
        return None, []

    # 点击「课件」Tab
    print("正在点击「课件」Tab...")
    tabs = content_frame.query_selector_all('.tab-item')
    for tab in tabs:
        if '课件' in tab.inner_text():
            tab.click()
            break

    page.wait_for_timeout(5000)

    # 获取「全部」图片
    all_imgs = get_slide_images(content_frame)
    print(f"  全部图片: {len(all_imgs)} 张")

    # 点击「习题」Tab
    print("正在切换到「习题」Tab...")
    sub_tabs = content_frame.query_selector_all('.tab-wrap .tab-item')
    for tab in sub_tabs:
        if tab.inner_text().strip() == '习题':
            tab.click()
            break

    page.wait_for_timeout(2000)

    # 获取习题图片
    exercise_imgs = get_slide_images(content_frame)
    print(f"  习题图片: {len(exercise_imgs)} 张")

    # 差集
    exercise_set = set(exercise_imgs)
    final_imgs = [img for img in all_imgs if img not in exercise_set]
    print(f"  非习题图片: {len(final_imgs)} 张")

    return lesson_title, final_imgs


def main():
    # 解析参数
    if len(sys.argv) < 2:
        print("用法:")
        print("  单个URL:  python spider.py <课程URL>")
        print("  批量处理: python spider.py -f <urls.txt>")
        print("\nurls.txt 格式: 每行一个URL")
        sys.exit(1)

    # 获取 URL 列表
    if sys.argv[1] == '-f':
        if len(sys.argv) < 3:
            print("请指定 URL 文件路径")
            sys.exit(1)
        urls_file = sys.argv[2]
        if not os.path.exists(urls_file):
            print(f"文件不存在: {urls_file}")
            sys.exit(1)
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"从文件读取到 {len(urls)} 个 URL")
    else:
        urls = [sys.argv[1]]

    login_url = "https://changjiang.yuketang.cn/web"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 登录
        print(f"正在打开登录页: {login_url}")
        page.goto(login_url)
        print("\n请在浏览器中完成登录后按回车...")
        input()

        # 收集所有课程的下载任务
        download_tasks = []

        for url in urls:
            try:
                lesson_title, img_urls = process_single_url(page, url)
                if lesson_title and img_urls:
                    download_tasks.append((lesson_title, img_urls))
            except Exception as e:
                print(f"  ✗ 处理失败: {e}")

        browser.close()

    # 批量下载
    if not download_tasks:
        print("\n没有找到任何图片")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"开始下载 {len(download_tasks)} 个课程的图片")
    print('='*60)

    total_success = 0
    total_fail = 0

    for lesson_title, img_urls in download_tasks:
        save_dir = os.path.join(os.getcwd(), lesson_title)
        os.makedirs(save_dir, exist_ok=True)

        print(f"\n下载: {lesson_title} ({len(img_urls)} 张)")
        print(f"保存到: {save_dir}")

        success, fail = download_images_parallel(img_urls, save_dir, lesson_title)
        total_success += success
        total_fail += fail

    print(f"\n{'='*60}")
    print(f"全部完成! 成功: {total_success}, 失败: {total_fail}")
    print('='*60)


if __name__ == '__main__':
    main()
