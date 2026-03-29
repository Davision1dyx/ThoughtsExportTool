# 阿里云云效知识库导出工具

一个用于批量导出阿里云云效（Thoughts）知识库文档到本地 Markdown 文件的工具。

## 功能特性

- 📚 **批量导出**：支持导出整个知识库的所有文档
- 📁 **保留结构**：保持原有的文件夹层级结构
- 📝 **Markdown 格式**：导出为标准的 Markdown 格式
- 🖼️ **图片支持**：自动提取文档中的图片并保留链接
- 💻 **代码块**：保留代码块的格式和语法高亮信息
- 📊 **表格支持**：将表格转换为 Markdown 表格格式
- 🔄 **顺序保持**：保持文档内容的原始顺序

## 环境要求

- Python 3.8+
- Playwright

## 安装

1. 克隆或下载本项目

2. 安装 Python 依赖：

```bash
pip install playwright
playwright install chromium
```

## 配置

1. 打开 `config.json` 文件

2. 配置 Cookie：
   - 登录阿里云云效（https://thoughts.aliyun.com）
   - 打开浏览器开发者工具（F12）
   - 切换到 Network 标签页
   - 刷新页面，找到任意 API 请求
   - 复制请求头中的 Cookie 值
   - 粘贴到 `config.json` 的 `cookies` 字段

3. 配置知识库 ID：
   - 打开要导出的知识库
   - 从 URL 中复制知识库 ID（如 `https://thoughts.aliyun.com/workspaces/xxx` 中的 `xxx`）
   - 粘贴到 `config.json` 的 `selected_workspaces` 数组中

示例配置：

```json
{
  "cookies": "your_cookie_string_here",
  "output_dir": "./output",
  "selected_workspaces": ["6963289eb0fc2e001bb052eb"]
}
```

## 使用方法

运行主程序：

```bash
python3 run_local_export.py
```

程序将自动：
1. 获取知识库中的所有文档列表
2. 逐个访问文档页面
3. 提取文档内容并转换为 Markdown
4. 按照原文件夹结构保存到 `output` 目录

## 输出结构

```
output/
└── 知识库名称/
    ├── 文件夹1/
    │   ├── 文档1.md
    │   └── 文档2.md
    ├── 文件夹2/
    │   └── 文档3.md
    └── 文档4.md
```

## 注意事项

1. **Cookie 有效期**：Cookie 可能会过期，如遇 401 错误请重新获取
2. **导出时间**：根据文档数量，导出可能需要较长时间（每篇文档约 3-5 秒）
3. **网络连接**：需要稳定的网络连接
4. **权限**：确保账号有访问目标知识库的权限

## 故障排除

### 401 Unauthorized 错误

Cookie 已过期，请重新从浏览器获取最新的 Cookie。

### 文档内容为空

可能是页面加载超时，可以尝试增加脚本中的等待时间。

### 图片无法显示

导出的 Markdown 文件中的图片链接是原始链接，需要网络访问权限才能查看。如需离线查看，需要额外下载图片。

## 技术说明

本工具使用 Playwright 模拟浏览器行为，因为云效文档内容是通过 WebSocket 动态加载的，无法直接通过 HTTP API 获取。

## 免责声明

本工具仅供学习和个人备份使用，请遵守阿里云云效的使用条款和相关法律法规。

## License

MIT License
