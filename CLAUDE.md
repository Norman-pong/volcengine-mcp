# volcengine_mcp — 火山引擎图片生成 MCP Server

## 项目概述

基于 [FastMCP](https://github.com/jlowin/fastmcp) 的 MCP Server，调用火山引擎方舟 API (`doubao-seedream-5-0-260128`) 实现文生图、图生图、多图融合、组图生成。生成的图片自动下载保存到本地目录。

## 技术栈

- **语言**: Python 3.8+
- **框架**: FastMCP (MCP 协议实现)
- **HTTP**: httpx (异步 HTTP 客户端)
- **图片处理**: Pillow (图片后处理)
- **包管理**: uv (推荐运行方式)
- **打包**: setuptools, PyPI (jimeng-mcp-volcengine)
- **CI**: GitHub Actions — release 时自动 publish 到 PyPI

## 项目结构

```
volcengine_mcp/
├── volcengine_mcp.py    # 主 MCP Server：工具定义、API 调用逻辑
├── image_processor.py   # 图片处理器：下载、保存、URL 识别
├── __main__.py          # python -m 入口
├── config.json          # MCP Client 配置示例（已脱敏）
├── setup.py             # 打包配置
├── requirements.txt     # 依赖
├── .env.example         # 环境变量示例
├── .gitignore
├── .github/workflows/   # CI: publish.yml
├── README.md
└── LICENSE              # MIT
```

## 架构要点

### API 认证
- 环境变量 `AITOKEN_VOLCENGINE` 提供 Bearer Token
- 未设置时工具返回明确的错误提示

### 图片生成流程
1. `volcengine_generate_image` 接收 prompt/参考图/参数
2. `_generate_single` 构建请求体，调用 `https://ark.cn-beijing.volces.com/api/v3/images/generations`
3. `ImageProcessor.process_response` 解析响应，下载 URL 图片到本地
4. 返回结果包含本地文件路径列表 `local_images`

### 三种生成模式
- **文生图**: 仅 prompt
- **图生图**: prompt + 参考图 URL (最多 10 张)
- **组图**: `sequential="auto"`, API 返回多张相关图片 (参考图+生成图 ≤ 15)

## 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `AITOKEN_VOLCENGINE` | 是 | 火山引擎方舟 API Key |
| `VOLCENGINE_OUTPUT_DIR` | 否 | 图片输出目录，默认 `./volcengine_images` |

## 开发约定

- 异步优先：所有 IO 操作使用 async/await + httpx.AsyncClient
- 错误处理：返回结构化 dict `{success: bool, error: str, ...}`，不抛异常
- 中文输出：print 和用户可见消息使用中文
- 无测试框架：目前无 test 目录或测试文件

## 安全注意事项

- **严禁**在代码、配置、README 中硬编码 API Key 或真实路径
- `.env` 已在 `.gitignore` 中，不应提交
- `config.json` 和 `.env.example` 中只放占位符
