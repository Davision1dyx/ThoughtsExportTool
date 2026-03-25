#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云云效知识库批量导出工具 - 浏览器自动化版
使用Playwright模拟浏览器操作，自动获取API数据

安装依赖:
    pip install playwright
    playwright install chromium
"""

import json
import os
import re
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
    children: List = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class YunxiaoBrowserDumper:
    """使用浏览器自动化导出云效知识库"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies = self.config.get('cookies', '')
        
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
    
    def parse_cookies(self) -> List[Dict]:
        """解析Cookie字符串为Playwright格式"""
        cookies_list = []
        for cookie_str in self.cookies.split(';'):
            cookie_str = cookie_str.strip()
            if '=' in cookie_str:
                name, value = cookie_str.split('=', 1)
                cookies_list.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.aliyun.com',
                    'path': '/',
                })
        return cookies_list
    
    async def dump(self):
        """执行导出"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # 设置为True可以隐藏浏览器窗口
            context = await browser.new_context()
            
            # 添加Cookie
            if self.cookies:
                cookies = self.parse_cookies()
                await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            print("正在访问云效知识库...")
            await page.goto('https://thoughts.aliyun.com/')
            
            # 等待页面加载
            await page.wait_for_timeout(3000)
            
            # 检查是否需要登录
            if 'login' in page.url or await page.query_selector('input[type="password"]') is not None:
                print("需要手动登录，请在浏览器中完成登录...")
                print("登录完成后按 Enter 键继续...")
                input()
            
            # 获取知识库列表
            print("正在获取知识库列表...")
            workspaces = await self._get_workspaces(page)
            
            if not workspaces:
                print("未找到知识库，请检查是否已登录")
                await browser.close()
                return
            
            print(f"\n发现 {len(workspaces)} 个知识库:")
            for i, ws in enumerate(workspaces, 1):
                print(f"  {i}. {ws.get('title', 'Unknown')}")
            
            # 导出每个知识库
            for workspace in workspaces:
                await self._dump_workspace(page, workspace)
            
            await browser.close()
    
    async def _get_workspaces(self, page) -> List[Dict]:
        """获取知识库列表"""
        # 拦截API请求获取数据
        workspaces = []
        
        # 方法1: 通过执行页面JavaScript获取
        try:
            # 等待知识库列表加载
            await page.wait_for_selector('[data-testid="workspace-item"], .workspace-item, .project-item', timeout=10000)
        except:
            pass
        
        # 尝试从页面的全局变量或API获取
        workspace_data = await page.evaluate("""
            () => {
                // 尝试从全局变量获取
                if (window.appData && window.appData.workspaces) {
                    return window.appData.workspaces;
                }
                if (window.workspaces) {
                    return window.workspaces;
                }
                
                // 尝试从DOM提取
                const items = document.querySelectorAll('[data-testid="workspace-item"], .workspace-item, .project-item, [data-project-id]');
                return Array.from(items).map(item => ({
                    id: item.dataset.projectId || item.dataset.workspaceId || item.dataset.id,
                    title: item.textContent?.trim() || 'Unknown'
                })).filter(w => w.id);
            }
        """)
        
        if workspace_data and len(workspace_data) > 0:
            return workspace_data
        
        # 方法2: 通过拦截网络请求获取
        # 先设置拦截器
        await page.route('**/api/**', lambda route: route.continue_())
        
        # 刷新页面触发请求
        await page.reload()
        await page.wait_for_timeout(3000)
        
        # 获取所有请求响应
        responses = []
        async def handle_response(response):
            if 'api' in response.url and ('workspace' in response.url or 'project' in response.url):
                try:
                    data = await response.json()
                    responses.append(data)
                except:
                    pass
        
        page.on('response', handle_response)
        
        # 等待一下收集响应
        await page.wait_for_timeout(2000)
        
        # 从响应中提取知识库数据
        for resp in responses:
            if isinstance(resp, dict):
                for key in ['data', 'result', 'workspaces', 'projects', 'list']:
                    if key in resp and isinstance(resp[key], list):
                        return resp[key]
        
        return []
    
    async def _dump_workspace(self, page, workspace: Dict):
        """导出单个知识库"""
        workspace_id = workspace.get('id') or workspace.get('_id') or workspace.get('projectId')
        workspace_title = workspace.get('title') or workspace.get('name') or 'Unknown'
        
        if not workspace_id:
            print(f"跳过无效知识库: {workspace_title}")
            return
        
        print(f"\n正在导出知识库: {workspace_title}")
        
        # 创建知识库目录
        safe_name = self._sanitize_filename(workspace_title)
        workspace_dir = self.output_dir / safe_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 访问知识库页面
        workspace_url = f"https://thoughts.aliyun.com/workspaces/{workspace_id}"
        print(f"  访问: {workspace_url}")
        await page.goto(workspace_url)
        await page.wait_for_timeout(3000)
        
        # 获取文档树
        documents = await self._get_documents_tree(page)
        print(f"  找到 {len(documents)} 个文档/文件夹")
        
        # 导出文档
        exported_count = await self._dump_documents(page, workspace_id, documents, workspace_dir)
        print(f"  导出完成: {exported_count} 个文档")
    
    async def _get_documents_tree(self, page) -> List[Dict]:
        """获取文档树"""
        # 等待文档列表加载
        try:
            await page.wait_for_selector('.doc-tree, .document-list, [data-testid="doc-item"], .node-item', timeout=10000)
        except:
            pass
        
        # 从页面提取文档树
        documents = await page.evaluate("""
            () => {
                // 尝试从全局变量获取
                if (window.docTree) {
                    return window.docTree;
                }
                if (window.documents) {
                    return window.documents;
                }
                
                // 从DOM提取
                const extractNodes = (container) => {
                    const nodes = [];
                    const items = container.querySelectorAll('.doc-item, .node-item, [data-doc-id], [data-node-id]');
                    
                    items.forEach(item => {
                        const id = item.dataset.docId || item.dataset.nodeId || item.dataset.id;
                        const titleEl = item.querySelector('.title, .name, .doc-title') || item;
                        const title = titleEl.textContent?.trim() || 'Untitled';
                        const isFolder = item.classList.contains('folder') || item.dataset.type === 'folder';
                        
                        const node = {
                            id: id,
                            title: title,
                            type: isFolder ? 'folder' : 'document'
                        };
                        
                        // 递归获取子节点
                        const childContainer = item.querySelector('.children, .doc-children');
                        if (childContainer) {
                            node.children = extractNodes(childContainer);
                        }
                        
                        nodes.push(node);
                    });
                    
                    return nodes;
                };
                
                const treeContainer = document.querySelector('.doc-tree, .document-tree, .sidebar, .nav-tree');
                if (treeContainer) {
                    return extractNodes(treeContainer);
                }
                
                return [];
            }
        """)
        
        return documents if documents else []
    
    async def _dump_documents(self, page, workspace_id: str, documents: List[Dict], 
                              parent_dir: Path, path_prefix: str = "") -> int:
        """递归导出文档"""
        exported_count = 0
        
        for doc in documents:
            doc_id = doc.get('id') or doc.get('_id')
            title = doc.get('title') or 'Untitled'
            doc_type = doc.get('type') or 'document'
            children = doc.get('children', [])
            
            if not doc_id:
                continue
            
            current_path = f"{path_prefix}/{title}" if path_prefix else title
            
            # 处理文件夹
            if doc_type == 'folder' or doc.get('isFolder'):
                folder_name = self._sanitize_filename(title)
                folder_dir = parent_dir / folder_name
                folder_dir.mkdir(parents=True, exist_ok=True)
                
                if children:
                    exported_count += await self._dump_documents(
                        page, workspace_id, children, folder_dir, current_path
                    )
                continue
            
            # 导出文档
            safe_title = self._sanitize_filename(title)
            output_path = parent_dir / f"{safe_title}.md"
            
            # 处理重名
            counter = 1
            while output_path.exists():
                output_path = parent_dir / f"{safe_title}_{counter}.md"
                counter += 1
            
            print(f"  导出: {current_path}")
            
            if await self._export_document(page, workspace_id, doc_id, output_path):
                exported_count += 1
            else:
                print(f"    失败: {title}")
        
        return exported_count
    
    async def _export_document(self, page, workspace_id: str, doc_id: str, 
                               output_path: Path) -> bool:
        """导出单个文档"""
        try:
            # 访问文档页面
            doc_url = f"https://thoughts.aliyun.com/workspaces/{workspace_id}/docs/{doc_id}"
            await page.goto(doc_url)
            await page.wait_for_timeout(2000)
            
            # 等待文档内容加载
            try:
                await page.wait_for_selector('.doc-content, .document-content, .editor-content, article', timeout=10000)
            except:
                pass
            
            # 尝试点击导出按钮获取Markdown
            # 方法1: 尝试使用导出功能
            try:
                # 查找更多/导出菜单
                more_btn = await page.query_selector('[data-testid="more-btn"], .more-actions, .export-btn, button[title="导出"]')
                if more_btn:
                    await more_btn.click()
                    await page.wait_for_timeout(500)
                    
                    # 点击导出Markdown选项
                    markdown_option = await page.query_selector('text=Markdown, [data-format="markdown"]')
                    if markdown_option:
                        await markdown_option.click()
                        await page.wait_for_timeout(2000)
                        
                        # 等待下载（这里需要处理下载事件）
                        # 简化处理：直接从页面提取内容
            except:
                pass
            
            # 方法2: 直接从页面提取内容
            doc_data = await page.evaluate("""
                () => {
                    const title = document.querySelector('h1, .doc-title, .document-title')?.textContent?.trim() || '';
                    const contentEl = document.querySelector('.doc-content, .document-content, .editor-content, article, .ProseMirror');
                    const html = contentEl?.innerHTML || '';
                    const text = contentEl?.innerText || '';
                    
                    // 尝试获取Markdown内容（如果有）
                    const markdown = window.docMarkdown || window.currentDoc?.content || '';
                    
                    return { title, html, text, markdown };
                }
            """)
            
            # 保存文档
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if doc_data.get('markdown'):
                content = doc_data['markdown']
            elif doc_data.get('html'):
                # 简单HTML转Markdown
                content = self._html_to_markdown(doc_data['html'])
            else:
                content = doc_data.get('text', '')
            
            # 添加YAML frontmatter
            frontmatter = f"""---
title: {doc_data.get('title', 'Untitled')}
source: {doc_url}
exported_at: {json.dumps(__import__('datetime').datetime.now().isoformat())}
---

"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter)
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"    导出错误: {e}")
            return False
    
    def _html_to_markdown(self, html: str) -> str:
        """简单HTML转Markdown"""
        # 这是一个简化版本，实际可以使用html2text库
        import re
        
        # 移除script和style标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # 转换标题
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n', html, flags=re.DOTALL)
        
        # 转换段落
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html, flags=re.DOTALL)
        
        # 转换粗体和斜体
        html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL)
        html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL)
        
        # 转换代码
        html = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', html, flags=re.DOTALL)
        html = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```', html, flags=re.DOTALL)
        
        # 转换链接
        html = re.sub(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL)
        
        # 转换图片
        html = re.sub(r'<img[^>]+src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/>', r'![\2](\1)', html)
        html = re.sub(r'<img[^>]+src="([^"]*)"[^>]*/>', r'![](\1)', html)
        
        # 转换列表
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL)
        html = re.sub(r'<ul[^>]*>(.*?)</ul>', r'\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<ol[^>]*>(.*?)</ol>', r'\1\n', html, flags=re.DOTALL)
        
        # 移除其他标签
        html = re.sub(r'<[^>]+>', '', html)
        
        # 解码HTML实体
        import html
        html = html.unescape(html)
        
        # 清理多余空行
        html = re.sub(r'\n{3,}', '\n\n', html)
        
        return html.strip()


async def main():
    """主函数"""
    print("=" * 60)
    print("阿里云云效知识库批量导出工具 (浏览器自动化版)")
    print("=" * 60)
    
    dumper = YunxiaoBrowserDumper()
    await dumper.dump()
    
    print("\n" + "=" * 60)
    print("导出完成!")
    print("=" * 60)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
