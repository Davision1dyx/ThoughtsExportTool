#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云云效知识库批量导出工具
支持将云效知识库(Thoughts)中的所有文档导出为Markdown格式，保留原始目录结构

使用方法:
1. 配置config.json文件
2. 运行: python yunxiao_dump.py
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Any
import http.cookiejar


class YunxiaoDumper:
    """云效知识库导出器"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化导出器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.cookies = self.config.get('cookies', '')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://thoughts.aliyun.com',
            'Referer': 'https://thoughts.aliyun.com/',
        }
        if self.cookies:
            self.headers['Cookie'] = self.cookies
        
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # API基础URL
        self.base_url = "https://thoughts.aliyun.com/api"
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _make_request(self, url: str, method: str = 'GET', data: Optional[Dict] = None) -> Optional[Dict]:
        """发送HTTP请求
        
        Args:
            url: 请求URL
            method: 请求方法
            data: 请求数据
            
        Returns:
            响应数据字典
        """
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8') if data else None,
                headers=self.headers,
                method=method
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
        except Exception as e:
            print(f"请求失败: {url}, 错误: {e}")
            return None
    
    def get_workspaces(self) -> List[Dict]:
        """获取知识库（工作空间）列表
        
        Returns:
            知识库列表
        """
        print("正在获取知识库列表...")
        
        # 尝试多种可能的API端点
        endpoints = [
            f"{self.base_url}/workspaces",
            f"{self.base_url}/v2/workspaces",
            "https://thoughts.aliyun.com/api/workspaces",
        ]
        
        for url in endpoints:
            result = self._make_request(url)
            if result and isinstance(result, dict):
                # 处理不同的响应格式
                data = result.get('data') or result.get('result') or result.get('workspaces') or result
                if isinstance(data, list):
                    print(f"找到 {len(data)} 个知识库")
                    return data
                elif isinstance(data, dict) and 'list' in data:
                    print(f"找到 {len(data['list'])} 个知识库")
                    return data['list']
        
        print("无法获取知识库列表，请检查Cookie是否有效")
        return []
    
    def get_documents(self, workspace_id: str) -> List[Dict]:
        """获取知识库中的文档列表
        
        Args:
            workspace_id: 知识库ID
            
        Returns:
            文档列表
        """
        print(f"正在获取知识库 {workspace_id} 的文档列表...")
        
        endpoints = [
            f"{self.base_url}/workspaces/{workspace_id}/documents",
            f"{self.base_url}/v2/workspaces/{workspace_id}/documents",
            f"{self.base_url}/workspaces/{workspace_id}/nodes",
            f"{self.base_url}/v2/workspaces/{workspace_id}/nodes",
        ]
        
        for url in endpoints:
            result = self._make_request(url)
            if result and isinstance(result, dict):
                data = result.get('data') or result.get('result') or result.get('documents') or result.get('nodes') or result
                if isinstance(data, list):
                    print(f"找到 {len(data)} 个文档/节点")
                    return data
                elif isinstance(data, dict) and 'list' in data:
                    print(f"找到 {len(data['list'])} 个文档/节点")
                    return data['list']
        
        return []
    
    def get_document_content(self, workspace_id: str, doc_id: str) -> Optional[Dict]:
        """获取文档内容
        
        Args:
            workspace_id: 知识库ID
            doc_id: 文档ID
            
        Returns:
            文档内容字典
        """
        endpoints = [
            f"{self.base_url}/workspaces/{workspace_id}/documents/{doc_id}",
            f"{self.base_url}/v2/workspaces/{workspace_id}/documents/{doc_id}",
            f"{self.base_url}/workspaces/{workspace_id}/nodes/{doc_id}",
        ]
        
        for url in endpoints:
            result = self._make_request(url)
            if result and isinstance(result, dict):
                return result.get('data') or result.get('result') or result
        
        return None
    
    def export_document_as_markdown(self, workspace_id: str, doc_id: str, output_path: Path) -> bool:
        """导出文档为Markdown格式
        
        Args:
            workspace_id: 知识库ID
            doc_id: 文档ID
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        # 尝试获取导出链接
        export_urls = [
            f"{self.base_url}/workspaces/{workspace_id}/documents/{doc_id}/export?format=markdown",
            f"{self.base_url}/workspaces/{workspace_id}/documents/{doc_id}/export/markdown",
            f"{self.base_url}/v2/workspaces/{workspace_id}/documents/{doc_id}/export?format=markdown",
        ]
        
        for url in export_urls:
            result = self._make_request(url)
            if result:
                # 处理不同的响应格式
                download_url = result.get('data', {}).get('url') if isinstance(result.get('data'), dict) else None
                download_url = download_url or result.get('url') or result.get('downloadUrl')
                
                if download_url:
                    try:
                        # 下载文件
                        req = urllib.request.Request(download_url, headers=self.headers)
                        with urllib.request.urlopen(req, timeout=60) as response:
                            content = response.read()
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, 'wb') as f:
                                f.write(content)
                        return True
                    except Exception as e:
                        print(f"下载失败: {e}")
        
        # 如果导出API不可用，尝试直接获取文档内容并转换
        doc_content = self.get_document_content(workspace_id, doc_id)
        if doc_content:
            return self._save_document_as_markdown(doc_content, output_path)
        
        return False
    
    def _save_document_as_markdown(self, doc_data: Dict, output_path: Path) -> bool:
        """将文档数据保存为Markdown文件
        
        Args:
            doc_data: 文档数据
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 提取标题和内容
            title = doc_data.get('title', 'untitled')
            content = doc_data.get('content', '')
            
            # 如果内容已经是markdown格式
            if doc_data.get('format') == 'markdown' or doc_data.get('type') == 'markdown':
                md_content = content
            else:
                # 尝试从其他格式转换
                md_content = self._convert_to_markdown(doc_data)
            
            # 添加YAML frontmatter
            frontmatter = self._generate_frontmatter(doc_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter)
                f.write('\n\n')
                f.write(md_content)
            
            return True
        except Exception as e:
            print(f"保存文档失败: {e}")
            return False
    
    def _convert_to_markdown(self, doc_data: Dict) -> str:
        """将文档内容转换为Markdown格式
        
        Args:
            doc_data: 文档数据
            
        Returns:
            Markdown格式内容
        """
        # 这里可以根据实际的文档格式进行转换
        # 目前简单返回内容，实际可能需要处理HTML、JSON等格式
        content = doc_data.get('content', '')
        
        # 如果是HTML内容，可以尝试转换
        if content.strip().startswith('<'):
            # 简单移除HTML标签（实际应该使用html2text等库）
            content = re.sub(r'<[^>]+>', '', content)
        
        return content
    
    def _generate_frontmatter(self, doc_data: Dict) -> str:
        """生成YAML frontmatter
        
        Args:
            doc_data: 文档数据
            
        Returns:
            YAML frontmatter字符串
        """
        frontmatter = {
            'title': doc_data.get('title', ''),
            'created': doc_data.get('createdAt', ''),
            'updated': doc_data.get('updatedAt', ''),
            'author': doc_data.get('creator', {}).get('name', '') if isinstance(doc_data.get('creator'), dict) else '',
        }
        
        lines = ['---']
        for key, value in frontmatter.items():
            if value:
                lines.append(f'{key}: {value}')
        lines.append('---')
        
        return '\n'.join(lines)
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        return filename or 'untitled'
    
    def dump_workspace(self, workspace: Dict, parent_dir: Optional[Path] = None) -> int:
        """导出单个知识库
        
        Args:
            workspace: 知识库信息
            parent_dir: 父目录
            
        Returns:
            导出的文档数量
        """
        workspace_id = workspace.get('id') or workspace.get('_id')
        workspace_name = workspace.get('name', 'unknown')
        
        if not workspace_id:
            print(f"知识库缺少ID: {workspace_name}")
            return 0
        
        print(f"\n正在导出知识库: {workspace_name}")
        
        # 创建知识库目录
        safe_name = self._sanitize_filename(workspace_name)
        workspace_dir = (parent_dir or self.output_dir) / safe_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存知识库元数据
        metadata_path = workspace_dir / '_workspace.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(workspace, f, ensure_ascii=False, indent=2)
        
        # 获取文档列表
        documents = self.get_documents(workspace_id)
        if not documents:
            print(f"知识库 {workspace_name} 中没有找到文档")
            return 0
        
        # 导出文档
        exported_count = 0
        for doc in documents:
            doc_id = doc.get('id') or doc.get('_id')
            doc_title = doc.get('title', 'untitled')
            doc_type = doc.get('type', 'document')
            
            if not doc_id:
                continue
            
            # 跳过文件夹节点，但递归处理其子节点
            if doc_type == 'folder' or doc.get('isFolder') or doc.get('is_directory'):
                folder_name = self._sanitize_filename(doc_title)
                folder_dir = workspace_dir / folder_name
                children = doc.get('children', [])
                if children:
                    exported_count += self._dump_documents_recursive(
                        workspace_id, children, folder_dir
                    )
                continue
            
            # 导出文档
            safe_title = self._sanitize_filename(doc_title)
            output_path = workspace_dir / f"{safe_title}.md"
            
            # 处理重名文件
            counter = 1
            original_path = output_path
            while output_path.exists():
                output_path = workspace_dir / f"{safe_title}_{counter}.md"
                counter += 1
            
            print(f"  导出: {doc_title} -> {output_path.name}")
            
            if self.export_document_as_markdown(workspace_id, doc_id, output_path):
                exported_count += 1
                time.sleep(0.5)  # 避免请求过快
            else:
                print(f"    导出失败: {doc_title}")
        
        print(f"知识库 {workspace_name} 导出完成，共导出 {exported_count} 个文档")
        return exported_count
    
    def _dump_documents_recursive(self, workspace_id: str, documents: List[Dict], parent_dir: Path) -> int:
        """递归导出文档
        
        Args:
            workspace_id: 知识库ID
            documents: 文档列表
            parent_dir: 父目录
            
        Returns:
            导出的文档数量
        """
        parent_dir.mkdir(parents=True, exist_ok=True)
        exported_count = 0
        
        for doc in documents:
            doc_id = doc.get('id') or doc.get('_id')
            doc_title = doc.get('title', 'untitled')
            doc_type = doc.get('type', 'document')
            
            if not doc_id:
                continue
            
            # 处理文件夹
            if doc_type == 'folder' or doc.get('isFolder') or doc.get('is_directory'):
                folder_name = self._sanitize_filename(doc_title)
                folder_dir = parent_dir / folder_name
                children = doc.get('children', [])
                if children:
                    exported_count += self._dump_documents_recursive(
                        workspace_id, children, folder_dir
                    )
                continue
            
            # 导出文档
            safe_title = self._sanitize_filename(doc_title)
            output_path = parent_dir / f"{safe_title}.md"
            
            # 处理重名文件
            counter = 1
            while output_path.exists():
                output_path = parent_dir / f"{safe_title}_{counter}.md"
                counter += 1
            
            print(f"  导出: {doc_title} -> {output_path.relative_to(self.output_dir)}")
            
            if self.export_document_as_markdown(workspace_id, doc_id, output_path):
                exported_count += 1
                time.sleep(0.5)
            else:
                print(f"    导出失败: {doc_title}")
        
        return exported_count
    
    def run(self):
        """运行导出流程"""
        print("=" * 50)
        print("阿里云云效知识库批量导出工具")
        print("=" * 50)
        
        # 检查配置
        if not self.cookies:
            print("错误: 请在 config.json 中配置 cookies")
            print("获取方法: 登录云效知识库后，从浏览器开发者工具中复制Cookie")
            return
        
        # 获取知识库列表
        workspaces = self.get_workspaces()
        if not workspaces:
            print("没有找到知识库或Cookie已过期")
            return
        
        # 显示知识库列表
        print("\n发现以下知识库:")
        for i, ws in enumerate(workspaces, 1):
            print(f"  {i}. {ws.get('name', 'unknown')}")
        
        # 选择要导出的知识库
        selected = self.config.get('selected_workspaces', [])
        if selected:
            workspaces = [ws for ws in workspaces if ws.get('id') or ws.get('_id') in selected]
        
        # 导出知识库
        total_exported = 0
        for workspace in workspaces:
            total_exported += self.dump_workspace(workspace)
        
        print("\n" + "=" * 50)
        print(f"导出完成! 共导出 {total_exported} 个文档")
        print(f"输出目录: {self.output_dir.absolute()}")
        print("=" * 50)


def main():
    """主函数"""
    dumper = YunxiaoDumper()
    dumper.run()


if __name__ == '__main__':
    main()
