"""
VITS TTS 插件

基于 artrajz-vits-simple-api 的文本转语音插件，支持多种语言和音色。

功能特性：
- 支持中文、英文、日文等多种语言
- 多种音色选择（通过id参数）
- Action自动触发和Command手动触发两种模式
- 支持配置文件自定义设置

使用方法：
- Action触发：发送包含"语音"、"说话"等关键词的消息
- Command触发：/vits 你好世界 [音色ID]

API接口：https://artrajz-vits-simple-api.hf.space/voice/vits
"""

from typing import List, Tuple, Type, Optional
import aiohttp
import asyncio
import tempfile
import uuid
import os
from urllib.parse import quote
from src.common.logger import get_logger
from src.plugin_system.base.base_plugin import BasePlugin
from src.plugin_system.apis.plugin_register_api import register_plugin
from src.plugin_system.base.base_action import BaseAction, ActionActivationType, ChatMode
from src.plugin_system.base.base_command import BaseCommand
from src.plugin_system.base.component_types import ComponentInfo
from src.plugin_system.base.config_types import ConfigField

logger = get_logger("vits_tts_plugin")

# ===== 共享工具类 =====
class VitsAPIClient:
    """VITS API客户端，提供统一的API调用接口"""

    @staticmethod
    async def call_vits_api(api_url: str, text: str, voice_id: str, language: str, timeout: int) -> Optional[str]:
        """调用VITS API生成语音"""
        try:
            # 构建请求URL
            encoded_text = quote(text)
            request_url = f"{api_url}?text={encoded_text}&id={voice_id}&lang={language}"

            logger.info(f"调用VITS API: {request_url}")
            logger.debug(f"请求参数 - 文本: {text[:100]}..., 音色ID: {voice_id}, 语言: {language}")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(request_url) as response:
                    logger.info(f"VITS API响应状态: {response.status}")
                    logger.debug(f"响应头: {dict(response.headers)}")

                    if response.status == 200:
                        # 检查响应内容类型
                        content_type = response.headers.get('content-type', '').lower()
                        logger.debug(f"响应内容类型: {content_type}")

                        # 读取音频数据
                        audio_data = await response.read()
                        logger.info(f"接收到音频数据大小: {len(audio_data)} 字节")

                        # 验证音频数据
                        if len(audio_data) < 100:  # 音频文件应该至少有100字节
                            logger.error(f"音频数据过小，可能损坏: {len(audio_data)} 字节")
                            return None

                        # 保存音频文件
                        filename = f"vits_tts_{uuid.uuid4().hex[:8]}.wav"
                        temp_path = tempfile.gettempdir()
                        audio_path = os.path.join(temp_path, filename)

                        with open(audio_path, "wb") as f:
                            f.write(audio_data)

                        logger.info(f"VITS音频文件生成成功: {audio_path}")
                        logger.debug(f"文件大小: {os.path.getsize(audio_path)} 字节")
                        return audio_path
                    else:
                        error_text = await response.text()
                        logger.error(f"VITS API调用失败: {response.status} - {error_text}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"VITS API调用超时 (超时时间: {timeout}秒)")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"VITS API网络错误: {e}")
            return None
        except Exception as e:
            logger.error(f"VITS API调用出错: {e}")
            return None

# ===== Action组件 =====
class VitsTTSAction(BaseAction):
    """VITS TTS Action - 智能语音合成"""
    
    action_name = "vits_tts_action"
    action_description = "使用VITS模型将文本转换为语音并发送"
    
    # 激活设置
    focus_activation_type = ActionActivationType.KEYWORD
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = False
    
    # 关键词激活
    activation_keywords = ["语音", "说话", "朗读", "念出来", "用语音说", "vits", "tts"]
    keyword_case_sensitive = False
    
    # Action参数
    action_parameters = {
        "text": "要转换为语音的文本内容",
        "voice_id": "音色ID，可选，默认为0"
    }
    action_require = [
        "当用户要求用语音回复时使用",
        "当用户说'用语音说'、'念出来'等时使用",
        "当需要语音播报重要信息时使用"
    ]
    associated_types = ["text"]
    
    async def execute(self) -> Tuple[bool, str]:
        """执行VITS TTS语音合成"""
        try:
            # 获取参数
            text = self.action_data.get("text", "").strip()
            voice_id = self.action_data.get("voice_id", "")

            if not text:
                await self.send_text("❌ 请提供要转换为语音的文本内容")
                return False, "缺少文本内容"

            # 从配置获取设置
            api_url = self.get_config("vits.api_url", "https://artrajz-vits-simple-api.hf.space/voice/vits")
            default_voice_id = self.get_config("vits.default_voice_id", "0")
            language = self.get_config("vits.language", "zh")
            timeout = self.get_config("vits.timeout", 30)
            max_text_length = self.get_config("vits.max_text_length", 500)

            # 检查文本长度
            if len(text) > max_text_length:
                await self.send_text(f"❌ 文本长度超过限制（最大{max_text_length}字符）")
                return False, f"文本长度超过限制: {len(text)}/{max_text_length}"

            # 使用默认音色ID如果未指定
            if not voice_id:
                voice_id = default_voice_id

            logger.info(f"{self.log_prefix} 开始VITS语音合成，文本：{text[:50]}..., 音色ID：{voice_id}")

            # 调用VITS API
            audio_path = await VitsAPIClient.call_vits_api(api_url, text, voice_id, language, timeout)

            if audio_path:
                # 发送语音文件
                await self.send_custom(message_type="voiceurl", content=audio_path)
                logger.info(f"{self.log_prefix} VITS语音发送成功")
                return True, f"成功生成并发送语音：{text[:30]}..."
            else:
                await self.send_text("❌ 语音合成失败，请检查网络连接或稍后重试")
                return False, "语音合成失败"

        except Exception as e:
            logger.error(f"{self.log_prefix} VITS语音合成出错: {e}")
            await self.send_text(f"❌ 语音合成出错: {str(e)}")
            return False, f"语音合成出错: {e}"

# ===== Command组件 =====
class VitsTTSCommand(BaseCommand):
    """VITS TTS Command - 手动语音合成命令"""
    
    command_name = "vits_tts_command"
    command_description = "使用VITS模型将文本转换为语音"
    
    # 命令匹配模式：/vits 文本内容 [音色ID]
    command_pattern = r"^/vits\s+(?P<text>.+?)(?:\s+(?P<voice_id>\d+))?$"
    command_help = "使用VITS将文本转换为语音。用法：/vits 你好世界 [音色ID]"
    command_examples = [
        "/vits 你好，世界！",
        "/vits 今天天气不错 1",
        "/vits こんにちは 2"
    ]
    intercept_message = True
    
    async def execute(self) -> Tuple[bool, str]:
        """执行VITS TTS命令"""
        try:
            # 获取匹配的参数
            text = self.matched_groups.get("text", "").strip()
            voice_id = self.matched_groups.get("voice_id", "")

            if not text:
                await self.send_text("❌ 请输入要转换为语音的文本内容")
                return False, "缺少文本内容"

            # 从配置获取设置
            api_url = self.get_config("vits.api_url", "https://artrajz-vits-simple-api.hf.space/voice/vits")
            default_voice_id = self.get_config("vits.default_voice_id", "0")
            language = self.get_config("vits.language", "zh")
            timeout = self.get_config("vits.timeout", 30)
            max_text_length = self.get_config("vits.max_text_length", 500)

            # 检查文本长度
            if len(text) > max_text_length:
                await self.send_text(f"❌ 文本长度超过限制（最大{max_text_length}字符）")
                return False, f"文本长度超过限制: {len(text)}/{max_text_length}"

            # 使用默认音色ID如果未指定
            if not voice_id:
                voice_id = default_voice_id

            logger.info(f"执行VITS命令，文本：{text[:50]}..., 音色ID：{voice_id}")

            # 调用VITS API
            audio_path = await VitsAPIClient.call_vits_api(api_url, text, voice_id, language, timeout)

            if audio_path:
                # 发送语音文件
                await self.send_type(message_type="voiceurl", content=audio_path)
                return True, f"成功生成并发送语音：{text[:30]}..."
            else:
                await self.send_text("❌ 语音合成失败，请检查网络连接或稍后重试")
                return False, "语音合成失败"

        except Exception as e:
            logger.error(f"VITS命令执行出错: {e}")
            await self.send_text(f"❌ 语音合成出错: {str(e)}")
            return False, f"语音合成出错: {e}"

# ===== 插件注册 =====
@register_plugin
class VitsTTSPlugin(BasePlugin):
    """VITS TTS插件 - 基于artrajz-vits-simple-api的文本转语音插件"""

    plugin_name = "vits_tts_plugin"
    plugin_description = "基于VITS模型的文本转语音插件，支持多种语言和音色"
    plugin_version = "1.0.0"
    plugin_author = "Augment Agent"
    enable_plugin = True
    config_file_name = "config.toml"
    dependencies = []  # 插件依赖列表
    python_dependencies = ["aiohttp"]  # Python包依赖列表
    
    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本配置",
        "components": "组件启用控制",
        "vits": "VITS API配置"
    }
    
    # 配置Schema定义
    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件")
        },
        "components": {
            "action_enabled": ConfigField(type=bool, default=True, description="是否启用Action组件"),
            "command_enabled": ConfigField(type=bool, default=True, description="是否启用Command组件")
        },
        "vits": {
            "api_url": ConfigField(
                type=str,
                default="https://artrajz-vits-simple-api.hf.space/voice/vits",
                description="VITS API地址"
            ),
            "default_voice_id": ConfigField(type=str, default="0", description="默认音色ID"),
            "language": ConfigField(type=str, default="zh", description="默认语言（zh/en/ja等）"),
            "timeout": ConfigField(type=int, default=30, description="API请求超时时间（秒）"),
            "max_text_length": ConfigField(type=int, default=500, description="最大文本长度限制"),
            "retry_count": ConfigField(type=int, default=2, description="API调用失败重试次数"),
            "audio_format": ConfigField(type=str, default="wav", description="音频文件格式")
        }
    }
    
    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""
        components = []

        # 根据配置决定是否启用组件（如果get_config方法不可用，则默认启用）
        try:
            action_enabled = self.get_config("components.action_enabled", True)
            command_enabled = self.get_config("components.command_enabled", True)
        except AttributeError:
            # 如果get_config方法不存在，默认启用所有组件
            action_enabled = True
            command_enabled = True

        if action_enabled:
            components.append((VitsTTSAction.get_action_info(), VitsTTSAction))

        if command_enabled:
            components.append((VitsTTSCommand.get_command_info(), VitsTTSCommand))

        return components
