# Alibaba Cloud Yunxiao Knowledge Base Export Tool

A tool for batch exporting documents from Alibaba Cloud Yunxiao (Thoughts) knowledge base to local Markdown files.

## Features

- 📚 **Batch Export**: Supports exporting all documents from the entire knowledge base
- 📁 **Structure Preservation**: Maintains the original folder hierarchy structure
- 📝 **Markdown Format**: Exports to standard Markdown format
- 🖼️ **Image Support**: Automatically extracts images from documents and preserves links
- 💻 **Code Blocks**: Preserves code block formatting and syntax highlighting information
- 📊 **Table Support**: Converts tables to Markdown table format
- 🔄 **Order Preservation**: Maintains the original order of document content

## Requirements

- Python 3.8+
- Playwright

## Installation

1. Clone or download this project

2. Install Python dependencies:

```bash
pip install playwright
playwright install
```

## Configuration

1. Open the `config.json` file

2. Configure Cookie:
   - Log in to Alibaba Cloud Yunxiao (https://thoughts.aliyun.com)
   - Open browser developer tools (F12)
   - Switch to the Network tab
   - Refresh the page and find any API request
   - Copy the Cookie value from the request headers
   - Paste it into the `cookies` field in `config.json`

3. Configure Workspace ID:
   - Open the knowledge base you want to export
   - Copy the workspace ID from the URL (e.g., `xxx` from `https://thoughts.aliyun.com/workspaces/xxx`)
   - Paste it into the `selected_workspaces` array in `config.json`

Example configuration:

```json
{
  "cookies": "your_cookie_string_here",
  "output_dir": "./output",
  "selected_workspaces": ["6963289eb0fc2e001bb052eb"]
}
```

## Usage

Run the main program:

```bash
python3 run_local_export.py
```

The program will automatically:
1. Get the list of all documents in the knowledge base
2. Visit each document page one by one
3. Extract document content and convert to Markdown
4. Save to the `output` directory according to the original folder structure

## Output Structure

```
output/
└── WorkspaceName/
    ├── Folder1/
    │   ├── Document1.md
    │   └── Document2.md
    ├── Folder2/
    │   └── Document3.md
    └── Document4.md
```

## Notes

1. **Cookie Validity**: Cookies may expire. If you encounter a 401 error, please obtain a new Cookie
2. **Export Time**: Depending on the number of documents, export may take a long time (approximately 3-5 seconds per document)
3. **Network Connection**: Requires stable network connection
4. **Permissions**: Ensure your account has access to the target knowledge base

## Troubleshooting

### 401 Unauthorized Error

The Cookie has expired. Please obtain the latest Cookie from your browser again.

### Empty Document Content

This may be due to page loading timeout. You can try increasing the wait time in the script.

### Images Not Displaying

The image links in the exported Markdown files are original links and require network access to view. For offline viewing, you need to download the images separately.

## Technical Notes

This tool uses Playwright to simulate browser behavior because Yunxiao document content is dynamically loaded via WebSocket and cannot be obtained directly through HTTP API.

## Disclaimer

This tool is for learning and personal backup purposes only. Please comply with Alibaba Cloud Yunxiao's terms of service and relevant laws and regulations.

## License

MIT License
