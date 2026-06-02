# 火山引擎图片生成 MCP Server

直接调用火山引擎方舟 API (doubao-seedream-5-0-260128) 的 MCP 服务器，支持文生图、图生图、多图融合、组图生成等全部功能。

## 功能

- 文生图：根据文字描述生成高质量图像
- 图生图：基于参考图片生成新图像
- 多图融合：融合多张参考图的元素（最多10张）
- 组图生成：一次生成多张主题相关的图片（最多15张）
- 批量处理：支持多个 prompt 批量生成
- 自动保存：生成的图片自动下载并保存到本地

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export AITOKEN_VOLCENGINE="your-api-key"
export VOLCENGINE_OUTPUT_DIR="./outputs"
```

### 3. 配置 MCP Client

```json
{
  "mcpServers": {
    "volcengine-image": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/volcengine_mcp",
        "python",
        "volcengine_mcp.py"
      ],
      "env": {
        "AITOKEN_VOLCENGINE": "your-api-key",
        "VOLCENGINE_OUTPUT_DIR": "~/Desktop/volcengine_images"
      }
    }
  }
}
```

## 使用示例

### 基础用法

```python
# 简单文生图
volcengine_generate_image("一只可爱的猫咪在花园里玩耍")

# 指定尺寸
volcengine_generate_image("壮丽的山水风景画", size="16:9")

# 关闭水印
volcengine_generate_image("产品图", watermark=False)
```

### 高级功能

#### 图生图（参考图生成）

```python
# 单张参考图
volcengine_generate_image("改为卡通风格", image="http://example.com/photo.jpg")

# 多张参考图融合
volcengine_generate_image(
    prompt="融合这些元素创造新场景",
    image=["url1.jpg", "url2.jpg", "url3.jpg"]
)
```

#### 组图生成

```python
# 示例1：生成3张不同时间的图片
volcengine_generate_image(
    prompt="生成3张不同时间段的海边风景：日出、正午、日落",
    sequential="auto",
    max_images=3
)

# 示例2：生成5张不同风格
volcengine_generate_image(
    prompt="生成5张不同艺术风格的花朵：油画、水彩、素描、国画、卡通",
    sequential="auto",
    max_images=5
)
```

#### 批量生成

```python
# 多prompt批量生成
volcengine_generate_image(["猫咪", "小狗", "兔子", "仓鼠"])
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prompt` | str/list | 必需 | 生成描述文本 |
| `image` | str/list | None | 参考图片URL（最多10张） |
| `size` | str | "1:1" | 图片尺寸比例 |
| `watermark` | bool | False | 是否添加水印 |
| `sequential` | str | "disabled" | 组图模式(auto/disabled) |
| `max_images` | int | 15 | 组图最大数量(1-15) |
| `stream` | bool | False | 是否流式传输 |

## 支持的尺寸

| 比例 | 像素值 | 适用场景 |
|------|--------|----------|
| `1:1` | 2048x2048 | 正方形，社交媒体 |
| `4:3` | 2304x1728 | 横向标准 |
| `3:4` | 1728x2304 | 纵向标准 |
| `16:9` | 2560x1440 | 宽屏，电影 |
| `9:16` | 1440x2560 | 竖屏，手机 |
| `3:2` | 2496x1664 | 横向照片 |
| `2:3` | 1664x2496 | 纵向照片 |
| `21:9` | 3024x1296 | 超宽屏 |

## 火山引擎配置

1. 注册火山引擎账号：https://console.volcengine.com/
2. 开通方舟（Ark）服务
3. 获取 API Key
4. 开通 `doubao-seedream-5-0-260128` 模型

## 注意事项

1. **API 限制**
   - 提示词建议 ≤300 汉字或 600 英文单词
   - 参考图最多 10 张，每张 ≤10MB
   - 组图生成：参考图+生成图总数 ≤15 张

2. **图片保存**
   - 默认保存到配置的输出目录
   - URL 格式的图片链接 24 小时后失效
   - 建议及时下载保存

3. **组图生成**
   - 使用 auto 模式时，在 prompt 中明确数量
   - 详细描述每张图的变化或特点
   - 合理设置 max_images 参数

## License

MIT License
