#!/usr/bin/env python3
"""
图片处理工具类
处理图片的下载、保存和URL识别
"""

import os
import re
import base64
import httpx
from typing import List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse, unquote
import mimetypes


class ImageProcessor:
    """图片处理器，负责下载、保存和管理生成的图片"""
    
    def __init__(self, output_dir: Optional[str] = None, provider: str = "volcengine"):
        """
        初始化图片处理器
        
        Args:
            output_dir: 输出目录，如果为None则使用环境变量或当前目录
            provider: 提供商标识，用于文件命名
        """
        self.provider = provider
        self.output_dir = self._setup_output_dir(output_dir)
        self.saved_images = []
        
        # URL匹配模式列表
        self.url_patterns = [
            # 带扩展名的标准格式
            r'https?://[^\s<>"]+\.(png|jpg|jpeg|gif|webp|bmp)(\?[^\s<>"]*)?',
            
            # 包含/image路径的URL
            r'https?://[^\s<>"]*/image[^\s<>"]*',
            
            # 特定CDN服务商
            r'https?://[^\s<>"]*(storage\.googleapis\.com|cdn\.openai\.com|oaidalleapi|dalle)[^\s<>"]*',
            
            # 火山引擎和其他CDN
            r'https?://[^\s<>"]*(s3\.ffire\.cc|google\.datas\.systems|volccdn\.com)[^\s<>"]*',
            
            # API格式URL
            r'https?://[^\s<>"]+/(v1|v2|api|cdn)/[^\s<>"]*',
            
            # Markdown格式识别
            r'!\[[^\]]*\]\((https?://[^\)]+)\)',
        ]
    
    def _setup_output_dir(self, output_dir: Optional[str]) -> str:
        """
        设置输出目录
        
        Args:
            output_dir: 指定的输出目录
            
        Returns:
            绝对路径形式的输出目录
        """
        if output_dir:
            dir_path = os.path.abspath(os.path.expanduser(output_dir))
        else:
            # 尝试从环境变量获取
            env_dir = os.getenv("VOLCENGINE_OUTPUT_DIR")
            if env_dir:
                dir_path = os.path.abspath(os.path.expanduser(env_dir))
            else:
                # 默认在当前目录创建子目录
                dir_path = os.path.abspath(f"./{self.provider}_images")
        
        # 确保目录存在
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 输出目录: {dir_path}")
        
        return dir_path
    
    def generate_filename(self, index: int = 1, extension: str = "png") -> str:
        """
        生成唯一的文件名
        
        Args:
            index: 图片序号
            extension: 文件扩展名
            
        Returns:
            文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.provider}_{timestamp}_{index}.{extension}"
    
    def detect_urls(self, text: str) -> List[str]:
        """
        从文本中检测所有图片URL
        
        Args:
            text: 要检测的文本
            
        Returns:
            找到的URL列表
        """
        urls = set()
        
        for pattern in self.url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # 处理可能的元组结果（从Markdown格式）
                if isinstance(match, tuple):
                    url = match[-1]  # 取最后一个捕获组
                else:
                    url = match
                
                # 清理URL
                url = url.strip()
                if url and url.startswith('http'):
                    urls.add(url)
        
        # 去重并排序
        url_list = sorted(list(urls))
        
        if url_list:
            print(f"🔍 发现 {len(url_list)} 个图片URL:")
            for url in url_list:
                print(f"   - {url[:80]}{'...' if len(url) > 80 else ''}")
        
        return url_list
    
    async def download_from_url(
        self, 
        url: str, 
        index: int = 1,
        timeout: int = 30
    ) -> Optional[str]:
        """
        从URL下载图片并保存
        
        Args:
            url: 图片URL
            index: 图片序号
            timeout: 超时时间（秒）
            
        Returns:
            保存的文件路径，失败返回None
        """
        try:
            print(f"⬇️  正在下载: {url[:80]}{'...' if len(url) > 80 else ''}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                # 从Content-Type获取扩展名
                content_type = response.headers.get('content-type', '').lower()
                extension = self._get_extension_from_content_type(content_type)
                
                # 如果无法从Content-Type获取，尝试从URL获取
                if not extension:
                    extension = self._get_extension_from_url(url)
                
                # 生成文件名和路径
                filename = self.generate_filename(index, extension)
                file_path = os.path.join(self.output_dir, filename)
                
                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                self.saved_images.append(file_path)
                print(f"✅ 已保存: {filename} (大小: {len(response.content)/1024:.1f}KB)")
                
                return file_path
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP错误 {e.response.status_code}: {url}")
        except httpx.TimeoutException:
            print(f"❌ 下载超时: {url}")
        except Exception as e:
            print(f"❌ 下载失败: {str(e)}")
        
        return None
    
    def save_from_base64(
        self, 
        base64_data: str, 
        index: int = 1,
        extension: str = "png"
    ) -> Optional[str]:
        """
        从Base64数据保存图片
        
        Args:
            base64_data: Base64编码的图片数据
            index: 图片序号
            extension: 文件扩展名
            
        Returns:
            保存的文件路径，失败返回None
        """
        try:
            # 移除可能的data:image前缀
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # 解码Base64
            image_data = base64.b64decode(base64_data)
            
            # 生成文件名和路径
            filename = self.generate_filename(index, extension)
            file_path = os.path.join(self.output_dir, filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            self.saved_images.append(file_path)
            print(f"✅ 已保存Base64图片: {filename}")
            
            return file_path
            
        except Exception as e:
            print(f"❌ 保存Base64图片失败: {str(e)}")
            return None
    
    def _get_extension_from_content_type(self, content_type: str) -> Optional[str]:
        """从Content-Type获取文件扩展名"""
        mime_to_ext = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp'
        }
        
        for mime, ext in mime_to_ext.items():
            if mime in content_type:
                return ext
        
        return None
    
    def _get_extension_from_url(self, url: str) -> str:
        """从URL获取文件扩展名"""
        path = urlparse(url).path
        path = unquote(path)  # 解码URL编码
        
        # 尝试从路径获取扩展名
        if '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']:
                return ext
        
        # 默认返回png
        return 'png'
    
    async def process_response(
        self, 
        response: dict,
        auto_download: bool = True
    ) -> dict:
        """
        处理API响应，下载并保存图片
        
        Args:
            response: API响应字典
            auto_download: 是否自动下载图片
            
        Returns:
            更新后的响应字典，包含本地文件路径
        """
        if not response.get('success'):
            return response
        
        # 检查是否有图片列表
        images = response.get('images', [])
        if not images:
            return response
        
        if not auto_download:
            return response
        
        # 处理每个图片
        local_paths = []
        for i, img in enumerate(images, 1):
            url = img.get('url')
            if url:
                # 下载并保存图片
                local_path = await self.download_from_url(url, i)
                if local_path:
                    local_paths.append(local_path)
                    # 添加本地路径到图片信息
                    img['local_path'] = local_path
        
        # 添加保存信息到响应
        if local_paths:
            response['local_images'] = local_paths
            response['output_dir'] = self.output_dir
            response['message'] = f"已保存 {len(local_paths)} 张图片到: {self.output_dir}"
        
        return response
    
    def get_saved_images(self) -> List[str]:
        """
        获取已保存的图片列表
        
        Returns:
            已保存图片的文件路径列表
        """
        return self.saved_images
    
    def clear_saved_list(self):
        """清空已保存图片列表"""
        self.saved_images = []
    
    def list_output_dir(self) -> List[str]:
        """
        列出输出目录中的所有图片文件
        
        Returns:
            图片文件路径列表
        """
        if not os.path.exists(self.output_dir):
            return []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
        images = []
        
        for file in os.listdir(self.output_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(os.path.join(self.output_dir, file))
        
        # 按修改时间排序（最新的在前）
        images.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        return images