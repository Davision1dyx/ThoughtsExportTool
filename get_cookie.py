#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云效Cookie获取辅助工具

提供多种方式获取云效知识库的访问Cookie:
1. 从浏览器数据库读取（支持Chrome/Edge/Firefox）
2. 手动输入
3. 从环境变量读取
"""

import os
import sys
import json
import sqlite3
import shutil
from pathlib import Path
from typing import Optional


def get_chrome_cookies(domain: str = "thoughts.aliyun.com") -> Optional[str]:
    """从Chrome浏览器获取Cookie
    
    Args:
        domain: 目标域名
        
    Returns:
        Cookie字符串
    """
    # 可能的Cookie数据库路径
    cookie_paths = [
        # macOS
        Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies",
        Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
        Path.home() / "Library/Application Support/Chromium/Default/Cookies",
        # Windows
        Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cookies",
        Path.home() / "AppData/Local/Google/Chrome/User Data/Profile 1/Cookies",
        # Linux
        Path.home() / ".config/google-chrome/Default/Cookies",
        Path.home() / ".config/chromium/Default/Cookies",
    ]
    
    for cookie_path in cookie_paths:
        if not cookie_path.exists():
            continue
        
        try:
            # 复制到临时位置（避免锁定）
            temp_db = Path("/tmp/chrome_cookies_temp.db")
            shutil.copy2(cookie_path, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # 查询Cookie
            cursor.execute("""
                SELECT name, value, host_key 
                FROM cookies 
                WHERE host_key LIKE ?
            """, (f"%{domain}%",))
            
            cookies = []
            for row in cursor.fetchall():
                name, value, host = row
                cookies.append(f"{name}={value}")
            
            conn.close()
            temp_db.unlink(missing_ok=True)
            
            if cookies:
                return "; ".join(cookies)
                
        except Exception as e:
            print(f"读取Chrome Cookie失败: {e}")
            continue
    
    return None


def get_edge_cookies(domain: str = "thoughts.aliyun.com") -> Optional[str]:
    """从Edge浏览器获取Cookie"""
    cookie_paths = [
        # macOS
        Path.home() / "Library/Application Support/Microsoft Edge/Default/Cookies",
        # Windows
        Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/Cookies",
    ]
    
    for cookie_path in cookie_paths:
        if not cookie_path.exists():
            continue
        
        try:
            temp_db = Path("/tmp/edge_cookies_temp.db")
            shutil.copy2(cookie_path, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name, value, host_key 
                FROM cookies 
                WHERE host_key LIKE ?
            """, (f"%{domain}%",))
            
            cookies = []
            for row in cursor.fetchall():
                name, value, host = row
                cookies.append(f"{name}={value}")
            
            conn.close()
            temp_db.unlink(missing_ok=True)
            
            if cookies:
                return "; ".join(cookies)
                
        except Exception as e:
            print(f"读取Edge Cookie失败: {e}")
            continue
    
    return None


def manual_input_cookie() -> str:
    """手动输入Cookie"""
    print("\n请手动输入Cookie字符串:")
    print("获取方法:")
    print("1. 登录云效知识库: https://thoughts.aliyun.com")
    print("2. 按F12打开开发者工具")
    print("3. 切换到 Network/网络 标签")
    print("4. 刷新页面，点击任意API请求")
    print("5. 在 Headers/请求头 中找到 Cookie 字段")
    print("6. 复制完整的Cookie值")
    print()
    
    cookie = input("Cookie: ").strip()
    return cookie


def save_cookie_to_config(cookie: str, config_path: str = "config.json"):
    """保存Cookie到配置文件"""
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    config['cookies'] = cookie
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"Cookie已保存到 {config_path}")


def main():
    """主函数"""
    print("=" * 50)
    print("云效Cookie获取工具")
    print("=" * 50)
    
    cookie = None
    
    # 尝试从浏览器获取
    print("\n正在尝试从浏览器获取Cookie...")
    
    cookie = get_chrome_cookies()
    if cookie:
        print("✓ 从Chrome浏览器获取到Cookie")
    else:
        cookie = get_edge_cookies()
        if cookie:
            print("✓ 从Edge浏览器获取到Cookie")
    
    # 如果自动获取失败，提示手动输入
    if not cookie:
        print("✗ 无法从浏览器自动获取Cookie")
        cookie = manual_input_cookie()
    
    # 验证并保存
    if cookie:
        print(f"\n获取到的Cookie长度: {len(cookie)} 字符")
        print("前100个字符预览:")
        print(cookie[:100] + "..." if len(cookie) > 100 else cookie)
        
        save = input("\n是否保存到配置文件? (y/n): ").strip().lower()
        if save == 'y':
            save_cookie_to_config(cookie)
    else:
        print("未能获取到Cookie")
        sys.exit(1)


if __name__ == '__main__':
    main()
