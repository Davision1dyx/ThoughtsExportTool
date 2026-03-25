#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云云效知识库批量导出工具 - 简化版
直接使用已知的知识库ID导出文档
"""

import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class YunxiaoSimpleDumper:
    """简化版云效知识库导出器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.cookies = self.config.get('cookies', '')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://thoughts.aliyun.com/',
            'Origin': 'https://thoughts.aliyun.com',
        }
        if self.cookies:
            self.headers['Cookie'] = self.cookies
        
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _make_request(self, url: str, retry: int = 2) -> Optional[Dict]:
        """发送HTTP请求"""
        for attempt in range(retry):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = response.read().decode('utf-8')
                    try:
                        return json.loads(data)
                    except:
                        return {'_raw': data}
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    print(f"  认证失败(401)，请检查Cookie是否有效")
                    return None
                print(f"  HTTP错误 {e.code}: {e.reason}")
                if attempt < retry - 1:
                    time.sleep(1)
            except Exception as e:
                print(f"  请求失败: {e}")
                if attempt < retry - 1:
                    time.sleep(1)
        return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        if len(filename) > 200:
            filename = filename[:200]
        return filename or 'untitled'
    
    def get_workspace_info(self, workspace_id: str) -> Optional[Dict]:
        """获取知识库信息"""
        # 尝试多种可能的API
        urls = [
            f"https://thoughts.aliyun.com/api/workspaces/{workspace_id}",
            f"https://thoughts.aliyun.com/api/v2/workspaces/{workspace_id}",
            f"https://thoughts.aliyun.com/api/projects/{workspace_id}",
        ]
        
        for url in urls:
            result = self._make_request(url)
            if result and not result.get('_raw'):
                return result.get('data', result)
        
        return None
    
    def get_all_nodes(self, workspace_id: str) -> List[Dict]:
        """获取知识库所有节点
        
        Args:
            workspace_id: 知识库ID
            
        Returns:
            所有节点列表
        """
        # 正确的API端点 - 获取所有节点
        url = f"https://thoughts.aliyun.com/api/workspaces/{workspace_id}/nodes"
        
        result = self._make_request(url)
        if result and not result.get('_raw'):
            # API返回格式: {"nextPageToken": "", "result": [...]}
            data = result.get('result', [])
            if isinstance(data, list):
                return data
        
        return []
    
    def get_nodes_by_parent(self, workspace_id: str, parent_id: str) -> List[Dict]:
        """获取指定父节点下的子节点
        
        Args:
            workspace_id: 知识库ID
            parent_id: 父节点ID
            
        Returns:
            子节点列表
        """
        # 使用 _parentId 参数获取子节点
        url = f"https://thoughts.aliyun.com/api/workspaces/{workspace_id}/nodes?pageSize=1000&_parentId={parent_id}"
        
        result = self._make_request(url)
        if result and not result.get('_raw'):
            data = result.get('result', [])
            if isinstance(data, list):
                return data
        
        return []
    
    def build_tree(self, nodes: List[Dict]) -> List[Dict]:
        """将扁平的节点列表构建成树形结构
        
        Args:
            nodes: 节点列表
            
        Returns:
            树形结构的根节点列表
        """
        # 创建ID到节点的映射
        node_map = {node.get('_id'): node for node in nodes if node.get('_id')}
        
        # 为每个节点添加children列表
        for node in nodes:
            node['children'] = []
        
        # 构建树
        roots = []
        for node in nodes:
            parent_id = node.get('_parentId')
            if parent_id and parent_id in node_map:
                # 有父节点，添加到父节点的children中
                parent = node_map[parent_id]
                parent['children'].append(node)
            else:
                # 没有父节点，是根节点
                roots.append(node)
        
        return roots
    
    def export_document(self, workspace_id: str, doc_id: str, output_path: Path) -> bool:
        """导出文档"""
        # 首先尝试获取文档内容
        url = f"https://thoughts.aliyun.com/api/workspaces/{workspace_id}/nodes/{doc_id}"
        
        result = self._make_request(url)
        if result:
            doc_data = result.get('data', result)
            return self._save_document(doc_data, output_path)
        
        return False
    
    def _save_document(self, doc_data: Dict, output_path: Path) -> bool:
        """保存文档为Markdown"""
        try:
            title = doc_data.get('title', 'Untitled')
            content = doc_data.get('content', '')
            
            # 构建Markdown
            md_content = f"""---
title: {title}
source: yunxiao-thoughts
exported_at: {datetime.now().isoformat()}
---

# {title}

{content}
"""
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            return True
        except Exception as e:
            print(f"    保存失败: {e}")
            return False
    
    def dump_workspace(self, workspace_id: str, workspace_name: str = None) -> int:
        """导出知识库"""
        print(f"\n正在导出知识库: {workspace_name or workspace_id}")
        
        # 获取知识库信息
        if not workspace_name:
            info = self.get_workspace_info(workspace_id)
            if info:
                workspace_name = info.get('title') or info.get('name', workspace_id)
            else:
                workspace_name = workspace_id
        
        # 创建目录
        safe_name = self._sanitize_filename(workspace_name)
        workspace_dir = self.output_dir / safe_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取所有节点
        all_nodes = self.get_all_nodes(workspace_id)
        if not all_nodes:
            print(f"  未找到文档或无法访问")
            return 0
        
        # 构建树形结构
        root_nodes = self.build_tree(all_nodes)
        print(f"  找到 {len(all_nodes)} 个节点，{len(root_nodes)} 个顶级目录")
        
        # 导出文档（递归处理文件夹）
        exported = self._dump_documents_recursive(workspace_id, root_nodes, workspace_dir)
        print(f"  成功导出 {exported} 个文档")
        
        return exported
    
    def _dump_documents_recursive(self, workspace_id: str, documents: List[Dict], 
                                   parent_dir: Path, processed_ids: set = None) -> int:
        """递归导出文档
        
        Args:
            workspace_id: 知识库ID
            documents: 文档列表
            parent_dir: 父目录
            processed_ids: 已处理的节点ID集合（防止循环）
        """
        if processed_ids is None:
            processed_ids = set()
        
        exported_count = 0
        
        for doc in documents:
            doc_id = doc.get('_id') or doc.get('id')
            title = doc.get('title') or 'Untitled'
            doc_type = doc.get('type', 'document')
            
            if not doc_id:
                continue
            
            # 防止循环处理
            if doc_id in processed_ids:
                continue
            processed_ids.add(doc_id)
            
            # 处理文件夹
            if doc_type == 'folder':
                folder_name = self._sanitize_filename(title)
                folder_dir = parent_dir / folder_name
                
                # 检查路径深度，防止过长
                try:
                    folder_dir.mkdir(parents=True, exist_ok=True)
                except OSError:
                    print(f"  跳过文件夹（路径过长）: {title}")
                    continue
                
                # 获取文件夹内的子节点
                children = self.get_nodes_by_parent(workspace_id, doc_id)
                if children:
                    print(f"    文件夹内有 {len(children)} 个子节点")
                    exported_count += self._dump_documents_recursive(
                        workspace_id, children, folder_dir, processed_ids
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
            
            print(f"  导出: {title}")
            
            if self.export_document(workspace_id, doc_id, output_path):
                exported_count += 1
                time.sleep(0.3)  # 限速
            else:
                print(f"    ✗ 失败")
        
        return exported_count
    
    def run(self):
        """运行导出"""
        print("=" * 60)
        print("阿里云云效知识库批量导出工具 (简化版)")
        print("=" * 60)
        
        if not self.cookies:
            print("错误: 请在 config.json 中配置 cookies")
            return
        
        # 获取要导出的知识库
        selected = self.config.get('selected_workspaces', [])
        
        if not selected:
            print("\n请在 config.json 的 selected_workspaces 中指定要导出的知识库ID")
            print("例如: [\"workspace_id_1\", \"workspace_id_2\"]")
            print("\n知识库ID获取方法:")
            print("1. 打开云效知识库网页")
            print("2. 进入目标知识库")
            print("3. 从URL中复制ID，如: https://thoughts.aliyun.com/workspaces/xxx 中的 xxx")
            return
        
        # 导出指定的知识库
        total = 0
        for workspace_id in selected:
            total += self.dump_workspace(workspace_id)
        
        print("\n" + "=" * 60)
        print(f"导出完成! 总计: {total} 个文档")
        print(f"输出目录: {self.output_dir.absolute()}")
        print("=" * 60)


def main():
    dumper = YunxiaoSimpleDumper()
    dumper.run()


if __name__ == '__main__':
    main()
