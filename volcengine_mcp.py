#!/usr/bin/env python3
"""
火山引擎图片生成 MCP Server
使用火山引擎 v3 API (Bearer Token认证)
支持序列图生成等高级功能
"""

import os
import httpx
from typing import Optional, Union, List, Dict, Any, Literal
from fastmcp import FastMCP
from image_processor import ImageProcessor

# 创建 FastMCP 实例
mcp = FastMCP("volcengine-image")

# API配置
AITOKEN_VOLCENGINE = os.getenv("AITOKEN_VOLCENGINE", "")
OUTPUT_DIR = os.getenv("VOLCENGINE_OUTPUT_DIR")
API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

# 创建图片处理器实例  
image_processor = ImageProcessor(output_dir=OUTPUT_DIR, provider="volcengine")


@mcp.tool()
async def volcengine_generate_image(
    prompt: Union[str, List[str]],
    image: Optional[Union[str, List[str]]] = None,
    size: str = "1:1",
    watermark: bool = False,
    sequential: Optional[Literal["auto", "disabled"]] = "disabled",
    max_images: int = 15,
    stream: bool = False
) -> Dict[str, Any]:
    """
    火山引擎图片生成工具。根据文字描述生成高质量图像，支持文生图、图生图、组图生成。

    当用户说"生成图片"、"画一张图"、"创建图像"、"画图"、"做一张图"、"生成一张...的图片"时调用此工具。
    当用户说"用火山引擎生成图片"、"用volcengine生成图片"、"用即梦生成图片"时调用此工具。
    当用户需要生成产品图、插画、海报、头像、风景图、人物图等任何图像时调用此工具。

    使用方式：
    1. 文生图：volcengine_generate_image("一只猫")
    2. 图生图：volcengine_generate_image("改为夜晚", image="http://...")
    3. 批量生成：volcengine_generate_image(["猫", "狗", "兔子"])
    4. 组图生成（重要！）：
       - volcengine_generate_image("生成3张不同时间段的城市风景：早晨、中午、夜晚", sequential="auto", max_images=3)
       - auto模式下，AI会根据prompt内容自动判断生成几张图
       - max_images参数限制最多生成数量（1-15张）
       - 在prompt中明确指出数量和场景描述效果最佳
            - 控制auto模式下最多生成几张图
            - 参考图数量 + 生成图数量 ≤ 15张
            - 建议根据prompt内容设置合理值
        stream: 是否流式传输
    
    图片自动保存到本地目录！
    """
    
    # 批量生成（多个不同的prompt）
    if isinstance(prompt, list):
        results = []
        for i, p in enumerate(prompt, 1):
            print(f"批量生成 [{i}/{len(prompt)}]: {p[:30]}...")
            result = await _generate_single(p, None, size, watermark, sequential, max_images, stream)
            results.append({
                "prompt": p,
                "success": result.get("success", False),
                "images": result.get("local_images", [])
            })
        
        return {
            "success": True,
            "mode": "批量生成",
            "total": len(prompt),
            "results": results,
            "output_dir": image_processor.output_dir
        }
    
    # 单个prompt生成（可能生成多张序列图）
    return await _generate_single(prompt, image, size, watermark, sequential, max_images, stream)


async def _generate_single(
    prompt: str,
    image_url: Optional[Union[str, List[str]]],
    size: str,
    watermark: bool,
    sequential: Optional[str],
    max_images: int,
    stream: bool
) -> Dict[str, Any]:
    if not AITOKEN_VOLCENGINE:
        return {
            "success": False,
            "error": "请设置环境变量 AITOKEN_VOLCENGINE",
            "hint": "export AITOKEN_VOLCENGINE='你的API密钥'"
        }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AITOKEN_VOLCENGINE}"
    }
    
    # 尺寸映射
    size_mapping = {
        "1:1": "2048x2048",
        "4:3": "2304x1728",
        "3:4": "1728x2304",
        "16:9": "2560x1440",
        "9:16": "1440x2560",
        "3:2": "2496x1664",
        "2:3": "1664x2496",
        "21:9": "3024x1296"
    }
    
    # 转换尺寸
    actual_size = size_mapping.get(size, size)
    
    # 构建请求体
    payload = {
        "model": "doubao-seedream-5-0-260128",
        "prompt": prompt,
        "size": actual_size,
        "response_format": "url",
        "watermark": watermark,
        "stream": stream
    }
    
    # 图生图模式
    if image_url:
        payload["image"] = image_url if isinstance(image_url, list) else [image_url]
    
    # 组图生成配置
    if sequential == "auto":
        payload["sequential_image_generation"] = "auto"
        # 验证max_images范围
        if max_images < 1 or max_images > 15:
            return {
                "success": False,
                "error": "参数错误：max_images必须在1-15之间",
                "hint": "组图生成最多支持15张"
            }
        # 检查参考图数量限制
        ref_count = len(image_url) if isinstance(image_url, list) else (1 if image_url else 0)
        if ref_count + max_images > 15:
            return {
                "success": False,
                "error": f"参数错误：参考图({ref_count}张) + 生成图({max_images}张) 总数不能超过15张",
                "hint": f"请减少max_images到{15 - ref_count}或更少"
            }
        payload["sequential_image_generation_options"] = {
            "max_images": max_images
        }
    else:
        payload["sequential_image_generation"] = "disabled"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=120.0  # 序列图生成需要更长时间
            )
            
            # 处理错误响应
            if response.status_code != 200:
                error_data = response.json()
                error_info = error_data.get("error", {})
                
                # 特殊处理模型未开通错误
                if error_info.get("code") == "ModelNotOpen":
                    return {
                        "success": False,
                        "error": "模型未开通",
                        "message": "请在火山引擎控制台开通 doubao-seedream-5-0-260128 模型",
                        "detail": error_info.get("message")
                    }
                
                return {
                    "success": False,
                    "error": f"API错误: {error_info.get('code', 'Unknown')}",
                    "message": error_info.get("message", "请求失败")
                }
            
            result = response.json()
            
            # 解析成功响应
            if "data" in result and result["data"]:
                images = result["data"]
                response_data = {
                    "success": True,
                    "mode": "组图" if sequential == "auto" else ("图生图" if image_url else "文生图"),
                    "prompt": prompt,
                    "images": [
                        {
                            "url": img.get("url", ""),
                            "width": img.get("width", 0),
                            "height": img.get("height", 0),
                            "revised_prompt": img.get("revised_prompt", "")
                        }
                        for img in images
                    ],
                    "created": result.get("created"),
                    "id": result.get("id")
                }
                
                # 自动下载并保存
                response_data = await image_processor.process_response(response_data)
                
                # 添加生成统计
                if response_data.get("local_images"):
                    response_data["message"] = f"成功生成 {len(response_data['local_images'])} 张图片"
                
                return response_data
            
            return {
                "success": False,
                "error": "响应格式错误",
                "detail": result
            }
                
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "请求超时",
            "hint": "图片生成时间较长，请稍后重试"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"请求失败: {str(e)}"
        }


def run_server():
    """入口函数，用于命令行调用"""
    mcp.run()

if __name__ == "__main__":
    run_server()