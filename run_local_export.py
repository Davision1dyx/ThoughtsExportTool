#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云云效知识库批量导出工具 - 本地运行版本

使用方法:
1. 确保已安装依赖:
   pip install playwright
   playwright install chromium

2. 运行脚本:
   python3 run_local_export.py
"""

import json
import os
import re
import asyncio
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional


class YunxiaoLocalExporter:
    """本地运行的云效知识库导出器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.cookies = self.config.get('cookies', '')
        self.workspace_id = self.config.get('selected_workspaces', [''])[0] if self.config.get('selected_workspaces') else ''
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _html_to_markdown(self, html: str) -> str:
        """将HTML转换为Markdown"""
        from html.parser import HTMLParser
        
        class MarkdownConverter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.result = []
                self.in_code = False
                self.code_lang = ''
                self.list_stack = []
                self.list_num = []
                
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    level = int(tag[1])
                    self.result.append('\n' + '#' * level + ' ')
                elif tag == 'p':
                    self.result.append('\n')
                elif tag == 'br':
                    self.result.append('\n')
                elif tag in ['strong', 'b']:
                    self.result.append('**')
                elif tag in ['em', 'i']:
                    self.result.append('*')
                elif tag == 'code':
                    if not self.in_code:
                        self.result.append('`')
                elif tag == 'pre':
                    self.in_code = True
                    self.code_lang = attrs_dict.get('data-language', '')
                    self.result.append(f'\n```{self.code_lang}\n')
                elif tag == 'blockquote':
                    self.result.append('\n> ')
                elif tag == 'ul':
                    self.list_stack.append('ul')
                    self.list_num.append(0)
                elif tag == 'ol':
                    self.list_stack.append('ol')
                    self.list_num.append(0)
                elif tag == 'li':
                    if self.list_stack:
                        depth = len(self.list_stack)
                        indent = '  ' * (depth - 1)
                        if self.list_stack[-1] == 'ul':
                            self.result.append(f'\n{indent}- ')
                        else:
                            self.list_num[-1] += 1
                            self.result.append(f'\n{indent}{self.list_num[-1]}. ')
                elif tag == 'a':
                    href = attrs_dict.get('href', '')
                    if href and not href.startswith('#'):
                        self.result.append('[')
                        self._href = href
                    else:
                        self._href = None
                elif tag == 'img':
                    src = attrs_dict.get('src', '')
                    alt = attrs_dict.get('alt', '')
                    if src:
                        self.result.append(f'![{alt}]({src})')
                elif tag == 'hr':
                    self.result.append('\n---\n')
                    
            def handle_endtag(self, tag):
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    self.result.append('\n\n')
                elif tag == 'p':
                    self.result.append('\n\n')
                elif tag in ['strong', 'b']:
                    self.result.append('**')
                elif tag in ['em', 'i']:
                    self.result.append('*')
                elif tag == 'code':
                    if not self.in_code:
                        self.result.append('`')
                elif tag == 'pre':
                    self.in_code = False
                    self.result.append('\n```\n\n')
                elif tag == 'blockquote':
                    self.result.append('\n')
                elif tag in ['ul', 'ol']:
                    if self.list_stack:
                        self.list_stack.pop()
                        self.list_num.pop()
                    self.result.append('\n')
                elif tag == 'a':
                    if hasattr(self, '_href') and self._href:
                        self.result.append(f']({self._href})')
                        self._href = None
                        
            def handle_data(self, data):
                # 转义特殊字符
                text = data.replace('*', '\\*').replace('_', '\\_')
                if self.in_code:
                    text = data  # 代码块内不转义
                self.result.append(text)
                
            def get_markdown(self):
                return ''.join(self.result).strip()
        
        try:
            converter = MarkdownConverter()
            converter.feed(html)
            return converter.get_markdown()
        except Exception as e:
            # 如果转换失败，返回纯文本
            import re
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', '', html)
            # 解码HTML实体
            text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
            return text
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        if len(filename) > 200:
            filename = filename[:200]
        return filename or 'untitled'
    
    def _parse_cookies(self, cookie_str: str) -> List[Dict]:
        """解析Cookie字符串为Playwright格式"""
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
    
    def _get_all_nodes(self) -> List[Dict]:
        """使用Python获取所有节点"""
        url = f'https://thoughts.aliyun.com/api/workspaces/{self.workspace_id}/nodes?pageSize=1000'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Cookie': self.cookies,
            'Referer': 'https://thoughts.aliyun.com/',
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get('result', [])
    
    def _get_nodes_by_parent(self, parent_id: str) -> List[Dict]:
        """获取指定父节点下的子节点"""
        url = f'https://thoughts.aliyun.com/api/workspaces/{self.workspace_id}/nodes?pageSize=1000&_parentId={parent_id}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Cookie': self.cookies,
            'Referer': 'https://thoughts.aliyun.com/',
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get('result', [])
    
    async def export(self):
        """执行导出"""
        from playwright.async_api import async_playwright
        
        # 1. 使用Python获取所有节点
        print("正在获取文档列表...")
        all_nodes = self._get_all_nodes()
        
        # 获取知识库名称（从第一个节点中）
        workspace_name = 'LLMentor'  # 默认值
        if all_nodes and len(all_nodes) > 0:
            if 'workspace' in all_nodes[0] and all_nodes[0]['workspace']:
                workspace_name = all_nodes[0]['workspace'].get('name', 'LLMentor')
        
        print(f"知识库名称: {workspace_name}")
        print(f"总共找到 {len(all_nodes)} 个节点")
        
        # 2. 构建目录结构
        folders = {n['_id']: n for n in all_nodes if n.get('type') == 'folder'}
        documents = [n for n in all_nodes if n.get('type') == 'document']
        
        print(f"  - 文件夹: {len(folders)} 个")
        print(f"  - 文档: {len(documents)} 个")
        
        # 创建输出目录
        safe_name = self._sanitize_filename(workspace_name)
        workspace_dir = self.output_dir / safe_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. 启动浏览器
        print("\n正在启动浏览器...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            
            # 添加Cookie - 需要为不同的domain添加
            if self.cookies:
                cookies_aliyun = []
                cookies_teambition = []
                for item in self.cookies.split(';'):
                    item = item.strip()
                    if '=' in item:
                        name, value = item.split('=', 1)
                        name = name.strip()
                        value = value.strip()
                        cookies_aliyun.append({
                            'name': name,
                            'value': value,
                            'domain': '.aliyun.com',
                            'path': '/',
                        })
                        cookies_teambition.append({
                            'name': name,
                            'value': value,
                            'domain': 'thoughts.aliyun.com',
                            'path': '/',
                        })
                await context.add_cookies(cookies_aliyun + cookies_teambition)
                print(f"已添加 {len(cookies_aliyun)} 个Cookie")
            
            page = await context.new_page()
            
            # 递归获取所有文档（包括子文件夹中的）
            all_documents = []
            
            def collect_documents(node_list, parent_path=""):
                for node in node_list:
                    if node.get('type') == 'document':
                        node['_export_path'] = parent_path
                        all_documents.append(node)
                    elif node.get('type') == 'folder':
                        folder_name = self._sanitize_filename(node.get('title', 'unknown'))
                        new_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
                        # 获取子节点
                        try:
                            children = self._get_nodes_by_parent(node['_id'])
                            collect_documents(children, new_path)
                        except Exception as e:
                            print(f"  获取文件夹 {node.get('title')} 内容失败: {e}")
            
            collect_documents(all_nodes)
            print(f"\n总共找到 {len(all_documents)} 个文档（包括子文件夹中的）")
            
            # 4. 导出每个文档
            exported = 0
            failed = 0
            
            for i, doc in enumerate(all_documents):
                doc_id = doc.get('_id')
                title = doc.get('title', 'Untitled')
                export_path = doc.get('_export_path', '')
                
                print(f"\n[{i+1}/{len(all_documents)}] 导出: {title}")
                
                try:
                    # 构建保存路径
                    if export_path:
                        save_dir = workspace_dir / export_path
                    else:
                        save_dir = workspace_dir
                    
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 访问文档页面
                    doc_url = f'https://thoughts.aliyun.com/workspaces/{self.workspace_id}/docs/{doc_id}'
                    await page.goto(doc_url)
                    
                    # 等待页面加载
                    await page.wait_for_timeout(5000)
                    try:
                        await page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        pass
                    await page.wait_for_timeout(3000)
                    
                    # 提取内容
                    content = ""
                    try:
                        # 从页面中提取结构化的 Markdown 内容 - 按文档顺序
                        content = await page.evaluate("""
                            () => {
                                const result = [];
                                
                                // 获取主要内容区域
                                const mainContent = document.querySelector('[data-slate-editor="true"]') || 
                                                   document.querySelector('.editor-content') ||
                                                   document.querySelector('[class*="content"]') ||
                                                   document.querySelector('main') || 
                                                   document.querySelector('article') ||
                                                   document.body;
                                
                                // 获取所有需要处理的元素，按文档顺序排序
                                const allElements = Array.from(mainContent.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, pre, table, img, div.image-wrapper__3eV0, div[class*="image-wrapper"]'));
                                
                                // 用于跟踪已处理的元素，避免重复
                                const processed = new Set();
                                let firstH1Skipped = false;  // 标记是否已跳过第一个 h1
                                
                                allElements.forEach(el => {
                                    if (processed.has(el)) return;
                                    
                                    const tag = el.tagName.toLowerCase();
                                    const className = el.className || '';
                                    
                                    // 如果元素在表格或代码块内（但不是表格或代码块本身），跳过
                                    if (tag !== 'table' && tag !== 'pre') {
                                        if (el.closest('table') || el.closest('pre')) return;
                                    }
                                    
                                    // 处理图片 - 包括 img 标签和图片包装器
                                    if (tag === 'img' || className.includes('image-wrapper')) {
                                        let img = el;
                                        if (tag !== 'img') {
                                            // 如果是包装器，查找内部的 img
                                            img = el.querySelector('img');
                                        }
                                        if (img) {
                                            const src = img.getAttribute('src');
                                            const alt = img.getAttribute('alt') || '';
                                            const imgClass = img.className || '';
                                            
                                            // 只保留文档中的图片
                                            const isDocImage = src && (
                                                src.includes('cdn.nlark.com') ||
                                                src.includes('yuque') ||
                                                imgClass.includes('image__') ||
                                                (!src.includes('thumbnail') && 
                                                 !src.includes('avatar') && 
                                                 !imgClass.includes('logo') &&
                                                 !imgClass.includes('icon__'))
                                            );
                                            
                                            if (isDocImage) {
                                                result.push('![' + alt + '](' + src + ')');
                                            }
                                            processed.add(img);
                                        }
                                        return;
                                    }
                                    
                                    // 处理代码块
                                    if (tag === 'pre') {
                                        const code = el.querySelector('code');
                                        if (code) {
                                            const langMatch = code.className.match(/language-(\\w+)/);
                                            let lang = langMatch ? langMatch[1] : '';
                                            if (!lang) {
                                                lang = code.getAttribute('data-language') || '';
                                            }
                                            
                                            const lines = code.querySelectorAll('.code-line__2r40, [class*="code-line"]');
                                            let codeText = '';
                                            if (lines.length > 0) {
                                                codeText = Array.from(lines).map(line => {
                                                    const content = line.querySelector('[data-slate-content="true"]');
                                                    return content ? content.textContent : line.textContent;
                                                }).join('\\n');
                                            } else {
                                                codeText = code.textContent;
                                            }
                                            
                                            if (codeText.trim()) {
                                                result.push('');
                                                result.push('```' + lang);
                                                result.push(codeText);
                                                result.push('```');
                                                result.push('');
                                            }
                                        }
                                        // 标记代码块内的所有元素为已处理
                                        el.querySelectorAll('*').forEach(child => processed.add(child));
                                        return;
                                    }
                                    
                                    // 处理表格
                                    if (tag === 'table') {
                                        const rows = el.querySelectorAll('tr');
                                        if (rows.length > 0) {
                                            let isFirstNonEmptyRow = true;
                                            
                                            rows.forEach((row) => {
                                                const cells = row.querySelectorAll('td, th');
                                                const cellTexts = Array.from(cells).map(cell => {
                                                    const content = cell.querySelector('[data-slate-content="true"]');
                                                    return content ? content.textContent.trim() : cell.textContent.trim();
                                                });
                                                
                                                // 跳过空行
                                                if (!cellTexts.some(t => t)) return;
                                                
                                                result.push('| ' + cellTexts.join(' | ') + ' |');
                                                
                                                // 第一个非空行后添加分隔行（表头）
                                                if (isFirstNonEmptyRow) {
                                                    const separators = cellTexts.map(() => '---');
                                                    result.push('| ' + separators.join(' | ') + ' |');
                                                    isFirstNonEmptyRow = false;
                                                }
                                            });
                                            result.push('');
                                        }
                                        // 标记表格内的所有元素为已处理
                                        el.querySelectorAll('*').forEach(child => processed.add(child));
                                        return;
                                    }
                                    
                                    // 处理文本元素
                                    const text = el.textContent.trim();
                                    if (!text) return;
                                    
                                    // 跳过第一个 h1（文档标题），避免与文件名重复
                                    if (tag === 'h1') {
                                        if (!firstH1Skipped) {
                                            firstH1Skipped = true;
                                            return;  // 跳过第一个 h1
                                        }
                                        result.push('# ' + text);
                                    }
                                    else if (tag === 'h2') result.push('## ' + text);
                                    else if (tag === 'h3') result.push('### ' + text);
                                    else if (tag === 'h4') result.push('#### ' + text);
                                    else if (tag === 'h5') result.push('##### ' + text);
                                    else if (tag === 'h6') result.push('###### ' + text);
                                    else if (tag === 'li') {
                                        const parent = el.parentElement;
                                        if (parent && parent.tagName.toLowerCase() === 'ul') {
                                            result.push('- ' + text);
                                        } else {
                                            const index = Array.from(parent.children).indexOf(el) + 1;
                                            result.push(index + '. ' + text);
                                        }
                                    }
                                    else if (tag === 'p') result.push(text);
                                });
                                
                                return result.join('\\n');
                            }
                        """)
                        
                        if not content or len(content) < 50:
                            # 备用方案：获取纯文本
                            content = await page.evaluate("""
                                () => {
                                    const elements = document.querySelectorAll('[data-slate-content="true"]');
                                    return Array.from(elements).map(el => el.textContent).join('\\n');
                                }
                            """)
                            
                    except Exception as e:
                        print(f"  警告: 提取内容时出错: {e}")
                        content = await page.evaluate("""
                            () => {
                                const elements = document.querySelectorAll('[data-slate-content="true"]');
                                return Array.from(elements).map(el => el.textContent).join('\\n');
                            }
                        """)
                    
                    # 保存文档
                    safe_title = self._sanitize_filename(title)
                    output_path = save_dir / f"{safe_title}.md"
                    
                    # 处理重名
                    counter = 1
                    while output_path.exists():
                        output_path = save_dir / f"{safe_title}_{counter}.md"
                        counter += 1
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {title}\n\n")
                        f.write(content)
                    
                    print(f"  ✓ 已保存: {output_path.name}")
                    exported += 1
                    
                    # 短暂休息，避免请求过快
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"  ✗ 导出失败: {e}")
                    failed += 1
            
            await browser.close()
            
            print(f"\n{'='*60}")
            print(f"导出完成!")
            print(f"  成功: {exported} 个文档")
            print(f"  失败: {failed} 个文档")
            print(f"  输出目录: {workspace_dir.absolute()}")
            print(f"{'='*60}")


async def main():
    print("="*60)
    print("阿里云云效知识库批量导出工具 (本地版)")
    print("="*60)
    
    # 检查配置
    if not os.path.exists('config.json'):
        print("\n错误: 找不到 config.json 配置文件")
        print("请确保配置文件存在并包含有效的 cookies 和 selected_workspaces")
        return
    
    exporter = YunxiaoLocalExporter()
    
    if not exporter.cookies:
        print("\n错误: 配置文件中缺少 cookies")
        return
    
    if not exporter.workspace_id:
        print("\n错误: 配置文件中缺少 selected_workspaces")
        return
    
    await exporter.export()


if __name__ == '__main__':
    asyncio.run(main())
