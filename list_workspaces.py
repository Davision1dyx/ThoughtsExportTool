#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取云效知识库列表
帮助用户找到正确的知识库ID
"""

import json
import os
import urllib.request
from pathlib import Path


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def make_request(url: str, cookies: str) -> dict:
    """发送HTTP请求"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Cookie': cookies,
        'Referer': 'https://thoughts.aliyun.com/',
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}


def main():
    print("=" * 60)
    print("获取云效知识库列表")
    print("=" * 60)
    
    config = load_config()
    cookies = config.get('cookies', '')
    
    if not cookies:
        print("\n错误: 请在 config.json 中配置 cookies")
        return
    
    print("\n正在尝试获取知识库列表...")
    print("(这可能需要几秒钟时间)\n")
    
    # 尝试多种API端点
    api_endpoints = [
        # 云效API
        "https://thoughts.aliyun.com/api/workspaces",
        "https://thoughts.aliyun.com/api/v2/workspaces",
        "https://thoughts.aliyun.com/api/projects",
        "https://thoughts.aliyun.com/api/v2/projects",
        
        # Teambition API
        "https://www.teambition.com/api/projects",
        "https://www.teambition.com/api/v2/projects",
        "https://www.teambition.com/api/workspaces",
        
        # 阿里云DevOps API
        "https://devops.aliyun.com/api/workspaces",
        "https://devops.aliyun.com/api/projects",
    ]
    
    found_workspaces = []
    
    for url in api_endpoints:
        print(f"尝试: {url}")
        result = make_request(url, cookies)
        
        if 'error' in result:
            print(f"  ✗ {result['error']}")
            continue
        
        # 解析响应
        data = None
        if isinstance(result, dict):
            for key in ['data', 'result', 'workspaces', 'projects', 'list']:
                if key in result:
                    data = result[key]
                    break
        
        if isinstance(data, list) and len(data) > 0:
            print(f"  ✓ 找到 {len(data)} 个知识库/项目")
            found_workspaces.extend(data)
        elif isinstance(data, dict) and 'list' in data:
            print(f"  ✓ 找到 {len(data['list'])} 个知识库/项目")
            found_workspaces.extend(data['list'])
        else:
            print(f"  - 未找到数据")
    
    # 去重
    seen_ids = set()
    unique_workspaces = []
    for ws in found_workspaces:
        ws_id = ws.get('_id') or ws.get('id') or ws.get('projectId')
        if ws_id and ws_id not in seen_ids:
            seen_ids.add(ws_id)
            unique_workspaces.append(ws)
    
    print("\n" + "=" * 60)
    if unique_workspaces:
        print(f"共找到 {len(unique_workspaces)} 个知识库:\n")
        for i, ws in enumerate(unique_workspaces, 1):
            ws_id = ws.get('_id') or ws.get('id') or ws.get('projectId', 'unknown')
            ws_name = ws.get('name') or ws.get('title') or 'Unknown'
            print(f"{i}. 名称: {ws_name}")
            print(f"   ID: {ws_id}")
            print()
        
        print("使用方法:")
        print("将上面的ID填入 config.json 的 selected_workspaces 中")
        print('例如: "selected_workspaces": ["' + unique_workspaces[0].get('_id', 'id') + '"]' )
    else:
        print("未能自动获取知识库列表")
        print("\n手动获取方法:")
        print("1. 打开浏览器，登录 https://thoughts.aliyun.com")
        print("2. 进入你想导出的知识库")
        print("3. 查看浏览器地址栏，URL格式为:")
        print("   https://thoughts.aliyun.com/workspaces/xxx")
        print("   其中的 'xxx' 就是知识库ID")
        print("4. 将ID填入 config.json 的 selected_workspaces 中")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
