# VITS TTS 插件

基于 [artrajz-vits-simple-api](https://artrajz-vits-simple-api.hf.space/) 的文本转语音插件，为 MaiCore 提供高质量的语音合成功能。

## 🎯 功能特性

- **多语言支持**：支持中文、英文、日文等多种语言
- **多音色选择**：通过音色ID参数选择不同的声音风格
- **双模式触发**：支持Action智能触发和Command手动触发
- **配置灵活**：支持自定义API地址、默认音色、语言等设置
- **智能优化**：文本长度限制、重试机制、音频验证
- **错误处理**：完善的错误处理和详细的日志记录
- **性能优化**：统一API客户端、异步处理、资源管理

## 📖 使用方法

### Action模式（智能触发）

当消息中包含以下关键词时，MaiCore可能会选择使用语音回复：

- "语音"、"说话"、"朗读"
- "念出来"、"用语音说"
- "vits"、"tts"

**示例：**
```
用户：用语音说一下今天的天气
麦麦：[发送语音消息]
```

### Command模式（手动触发）

使用 `/vits` 命令直接生成语音：

```bash
/vits 你好，世界！              # 使用默认音色
/vits 今天天气不错 1            # 使用音色ID为1的声音
/vits こんにちは 2             # 使用音色ID为2的声音
```

## ⚙️ 配置说明

插件启动后会自动生成 `config.toml` 配置文件，包含以下配置项：

### 插件基本配置
```toml
[plugin]
enabled = true  # 是否启用插件
```

### 组件控制
```toml
[components]
action_enabled = true   # 是否启用Action组件（智能触发）
command_enabled = true  # 是否启用Command组件（手动触发）
```

### VITS API配置
```toml
[vits]
api_url = "https://artrajz-vits-simple-api.hf.space/voice/vits"  # API地址
default_voice_id = "0"    # 默认音色ID
language = "zh"           # 默认语言（zh/en/ja等）
timeout = 30              # API请求超时时间（秒）
max_text_length = 500     # 最大文本长度限制
retry_count = 2           # API调用失败重试次数
audio_format = "wav"      # 音频文件格式
```

## 🎵 音色说明

该插件使用的API支持多种音色，通过 `id` 参数控制：

- `0`：默认音色
- `1`、`2`、`3`...：其他可用音色

具体可用的音色ID需要参考API文档或通过测试确定。

## 🌍 语言支持

支持的语言代码：

- `zh`：中文
- `en`：英文  
- `ja`：日文
- 其他语言请参考API文档

## � 优化特性

### 代码优化
- **统一API客户端**：消除了Action和Command组件中的重复代码
- **增强错误处理**：添加了详细的错误信息和网络错误分类
- **音频验证**：检查音频文件大小和格式，确保生成质量
- **文本长度限制**：防止过长文本导致的API调用失败
- **重试机制**：支持配置API调用失败重试次数

### 性能优化
- **异步处理**：完全异步的API调用，不阻塞主线程
- **资源管理**：自动清理临时文件，优化内存使用
- **详细日志**：分级日志记录，便于调试和监控

## �🔧 技术细节

### 插件架构

- **继承BasePlugin**：实现了所有必需的抽象方法
- **VitsAPIClient**：统一的API客户端类，提供可复用的API调用逻辑
- **dependencies()**: 返回插件依赖列表（本插件无依赖）
- **python_dependencies()**: 返回Python包依赖（aiohttp）
- **配置Schema驱动**：自动生成配置文件，无需手动创建

### API接口

插件调用的API接口格式：
```
GET https://artrajz-vits-simple-api.hf.space/voice/vits?text={文本}&id={音色ID}&lang={语言}
```

### 文件处理

- 生成的音频文件保存在系统临时目录
- 文件名格式：`vits_tts_{随机ID}.wav`
- 通过 `voiceurl` 消息类型发送语音

### 错误处理

- API调用超时处理
- 网络错误重试机制
- 详细的错误日志记录
- 用户友好的错误提示



## 🐛 故障排除

### 常见问题

1. **语音合成失败**：检查网络连接和API地址
2. **音色不生效**：确认音色ID是否有效
3. **超时问题**：增加timeout配置值

## 📄 许可证

本插件遵循MIT许可证。
