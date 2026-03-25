#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本 - 检查页面内容
"""

import asyncio
import json
import os
from pathlib import Path

async def debug():
    from playwright.async_api import async_playwright
    
    # 加载配置
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    cookies_str = config.get('cookies', '')
    workspace_id = config.get('selected_workspaces', [''])[0]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # 添加Cookie - 需要为不同的domain添加
        if cookies_str:
            cookies_aliyun = []
            cookies_teambition = []
            for item in cookies_str.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    # 为 aliyun.com 添加
                    cookies_aliyun.append({
                        'name': name,
                        'value': value,
                        'domain': '.aliyun.com',
                        'path': '/',
                    })
                    # 为 thoughts.aliyun.com 添加
                    cookies_teambition.append({
                        'name': name,
                        'value': value,
                        'domain': 'thoughts.aliyun.com',
                        'path': '/',
                    })
            await context.add_cookies(cookies_aliyun + cookies_teambition)
            print(f"已添加 {len(cookies_aliyun)} 个Cookie到 aliyun.com")
            print(f"已添加 {len(cookies_teambition)} 个Cookie到 thoughts.aliyun.com")
        
        page = await context.new_page()
        
        # 访问两个测试文档
        test_docs = [
            ('696387d23fb9180001f4186d', '✅理解 OpenAI API'),  # 提示词工程/理解 OpenAI API
            ('69664a173fb9180001f7a826', '✅Java中大模型调用的多种方式'),  # 初探SpringAI/Java中大模型调用的多种方式
        ]
        
        for doc_id, doc_title in test_docs:
            print(f"\n{'='*60}")
            print(f"检查文档: {doc_title}")
            print(f"{'='*60}")
            
            doc_url = f'https://thoughts.aliyun.com/workspaces/{workspace_id}/docs/{doc_id}'
        
            print(f"访问: {doc_url}")
            
            # 访问文档页面
            await page.goto(doc_url)
            await page.wait_for_timeout(8000)
            
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass
            await page.wait_for_timeout(3000)
            
            # 检查页面标题
            title = await page.title()
            print(f"页面标题: {title}")
            
            # 获取页面HTML
            html = await page.content()
            
            # 分析HTML结构
            print("\n分析HTML结构...")
            
            # 查找代码块
            import re
            code_blocks = re.findall(r'<div[^>]*class="[^"]*code[^"]*"[^>]*>.*?</div>', html, re.DOTALL | re.IGNORECASE)
            print(f"找到 {len(code_blocks)} 个代码块div")
            if code_blocks:
                print("代码块示例:")
                print(code_blocks[0][:500])
            
            # 查找表格
            tables = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL | re.IGNORECASE)
            print(f"\n找到 {len(tables)} 个表格")
            if tables:
                print("表格示例:")
                print(tables[0][:500])
            
            # 查找 slate 结构
            slate_elements = re.findall(r'<[^>]*data-slate[^>]*>', html)
            print(f"\n找到 {len(slate_elements)} 个 slate 元素")
            
            # 保存HTML供分析
            filename = f'debug_{doc_title.replace(" ", "_").replace("/", "_")}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\nHTML已保存: {filename}")
            
            # 提取内容测试
            print("\n测试内容提取:")
            content = await page.evaluate("""
                () => {
                    // 获取所有文本节点及其父元素信息
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    const results = [];
                    let node;
                    while (node = walker.nextNode()) {
                        const parent = node.parentElement;
                        const grandparent = parent ? parent.parentElement : null;
                        
                        // 获取元素的类名和标签
                        const parentInfo = parent ? `${parent.tagName}.${parent.className}` : 'none';
                        const text = node.textContent.trim();
                        
                        if (text && text.length > 0) {
                            results.push({
                                text: text.substring(0, 100),
                                parent: parentInfo
                            });
                        }
                    }
                    
                    return results.slice(0, 30);  // 返回前30个
                }
            """)
            
            for item in content[:20]:
                print(f"  [{item['parent']}] {item['text'][:50]}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug())
