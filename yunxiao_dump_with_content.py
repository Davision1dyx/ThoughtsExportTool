#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云云效知识库批量导出工具 - 带内容获取
使用Playwright浏览器自动化获取文档完整内容

安装依赖:
    pip install playwright
    playwright install chromium
"""

import json
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Document:
    """文档数据类"""
    id: str
    title: str
    content: str = ""
    doc_type: str = "document"
    path: str = ""


class YunxiaoContentDumper:
    """带内容获取的云效知识库导出器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.cookies = self.config.get('cookies', '')
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        if len(filename) > 200:
            filename = filename[:200]
        return filename or 'untitled'
    
    async def dump(self):
        """执行导出"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context()
            
            # 添加Cookie
            if self.cookies:
                cookies_list = self._parse_cookies(self.cookies)
                await context.add_cookies(cookies_list)
            
            page = await context.new_page()
            
            print("正在访问云效知识库...")
            await page.goto('https://thoughts.aliyun.com/')
            await page.wait_for_timeout(3000)
            
            # 获取知识库列表
            workspaces = await self._get_workspaces(page)
            
            if not workspaces:
                print("未找到知识库")
                await browser.close()
                return
            
            print(f"\n发现 {len(workspaces)} 个知识库")
            
            # 导出每个知识库
            for workspace in workspaces:
                await self._dump_workspace(page, workspace)
            
            await browser.close()
    
    def _parse_cookies(self, cookie_str: str) -> List[Dict]:
        """解析Cookie字符串"""
        cookies = []
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.aliyun.com',
                    'path': '/',
                })
        return cookies
    
    async def _get_workspaces(self, page) -> List[Dict]:
        """获取知识库列表"""
        # 使用配置中的知识库ID
        selected = self.config.get('selected_workspaces', [])
        if not selected:
            print("错误: 请在 config.json 中配置 selected_workspaces")
            return []
        
        # 获取知识库信息
        workspaces = []
        for ws_id in selected:
            try:
                url = f'https://thoughts.aliyun.com/api/workspaces/{ws_id}'
                response = await page.evaluate(f"""
                    async () => {{
                        const resp = await fetch('{url}');
                        const data = await resp.json();
                        return data.data || null;
                    }}
                """)
                if response:
                    workspaces.append(response)
            except Exception as e:
                print(f"获取知识库 {ws_id} 信息失败: {e}")
        
        return workspaces
    
    async def _dump_workspace(self, page, workspace: Dict):
        """导出单个知识库"""
        workspace_id = workspace.get('_id')
        workspace_name = workspace.get('name', 'unknown')
        
        print(f"\n导出知识库: {workspace_name}")
        
        # 创建目录
        safe_name = self._sanitize_filename(workspace_name)
        workspace_dir = self.output_dir / safe_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取所有节点
        url = f'https://thoughts.aliyun.com/api/workspaces/{workspace_id}/nodes?pageSize=1000'
        nodes_data = await page.evaluate(f"""
            async () => {{
                const resp = await fetch('{url}');
                const data = await resp.json();
                return data.result || [];
            }}
        """)
        
        # 筛选出文档类型的节点
        doc_nodes = [n for n in nodes_data if n.get('type') == 'document']
        print(f"  找到 {len(doc_nodes)} 个文档")
        
        exported = 0
        for node in doc_nodes:
            try:
                doc_id = node.get('_id')
                title = node.get('title', 'Untitled')
                
                print(f"  导出: {title}")
                
                # 访问文档页面
                doc_url = f'https://thoughts.aliyun.com/workspaces/{workspace_id}/docs/{doc_id}'
                await page.goto(doc_url)
                await page.wait_for_timeout(5000)  # 等待内容加载
                
                # 等待编辑器内容加载
                try:
                    await page.wait_for_selector('.ProseMirror, .doc-content, article, [contenteditable="true"]', timeout=15000)
                except:
                    print(f"    等待内容超时，尝试获取页面文本")
                
                # 提取内容 - 尝试多种选择器
                content = await page.evaluate("""
                    () => {
                        // 尝试找到编辑器内容
                        const selectors = [
                            '.ProseMirror',
                            '.doc-content',
                            'article',
                            '[contenteditable="true"]',
                            '.editor-content',
                            '#editor',
                            '.document-body'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.innerText.trim().length > 50) {
                                return el.innerText;
                            }
                        }
                        
                        // 如果找不到特定编辑器，获取主要内容区域
                        const main = document.querySelector('main, .main, .content, #content');
                        if (main) return main.innerText;
                        
                        // 最后尝试body
                        return document.body.innerText;
                    }
                """)
                
                # 保存文档
                safe_title = self._sanitize_filename(title)
                output_path = workspace_dir / f"{safe_title}.md"
                
                counter = 1
                while output_path.exists():
                    output_path = workspace_dir / f"{safe_title}_{counter}.md"
                    counter += 1
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {title}\n\n")
                    f.write(content)
                
                exported += 1
                await asyncio.sleep(1)  # 避免请求过快
                
            except Exception as e:
                print(f"    错误: {e}")
        
        print(f"  成功导出 {exported} 个文档")


async def main():
    print("=" * 60)
    print("阿里云云效知识库批量导出工具 (带内容获取)")
    print("=" * 60)
    
    dumper = YunxiaoContentDumper()
    await dumper.dump()
    
    print("\n" + "=" * 60)
    print("导出完成!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
