# siliconflow-chat-gui

一个由 SiliconFlow API 驱动的轻量级 Streamlit 聊天界面。

支持文本和图像输入（VLM），能够以流式传输响应并附带可选的推理模式，同时将聊天记录保存在本地。

> 界面为中文，开箱即用；需要先配置环境变量 `SILICONFLOW_API_KEY`。

## 功能特性

  - 基于 Streamlit 的聊天界面，支持流式响应
  - 支持文本和图像的多模态输入（上传图片后会自动切换到 VLM）
  - 对于支持的模型，可选择性显示推理过程内容
  - 侧边栏提供模型选择器和生成参数控制（max\_tokens、temperature、top\_p）
  - 本地聊天记录功能，支持自动命名、加载和删除
  - 可与 SiliconFlow API 配合使用（请访问[https://api.siliconflow.cn](https://api.siliconflow.cn)获取API KEY）

## 环境要求

  - Python 3.10+
  - 一个拥有所选模型访问权限的 SiliconFlow API 密钥

## 快速开始 (Windows)

```powershell
# 1) 安装依赖
pip install -r requirements.txt

# 2) 配置你的 SiliconFlow API 密钥
setx SILICONFLOW_API_KEY "sk-your-key"

# 重启 PowerShell (或新开一个) 以使 setx 生效，然后运行应用
streamlit run GUI.py
```

在 macOS/Linux (bash) 上:

```bash
pip3 install -r requirements.txt
export SILICONFLOW_API_KEY="sk-your-key"
streamlit run GUI.py
```

## 配置

  - **API 密钥**：通过环境变量 `SILICONFLOW_API_KEY` 设置。
  - **API 基地址**：`https://api.siliconflow.cn/v1/chat/completions`（在 `GUI.py` 文件中配置）。
  - **模型**：
      - **文本模型**：可在侧边栏选择，已提供部分例子：
          - `deepseek-ai/DeepSeek-V3.1`
          - `Qwen/Qwen3-235B-A22B-Thinking-2507`
          - `zai-org/GLM-4.5`
          - `Pro/deepseek-ai/DeepSeek-V3.1`
      - **视觉模型**：上传图片后自动选择为 `zai-org/GLM-4.5V`。
  - **推理过程**：对于支持的混合模型会自动启用。

## 使用方法

1.  在浏览器中打开应用（Streamlit 会自动打开，默认地址为 http://localhost:8501）。
2.  在侧边栏调整模型和生成参数。
3.  输入你的提示词。在发送前，你也可以选择上传一张或多张图片。
4.  实时观察答案的流式输出；如果可用，可以展开“推理过程/Reasoning”部分查看追踪信息。
5.  聊天记录会保存到 `ChatHistory/` 文件夹中，并可以从侧边栏重新打开或删除。

## 注意事项

  - 上传的图片会被编码为 base64 数据 URL 并发送给 VLM。
  - 聊天记录的名称是通过一次轻量级的命名调用自动生成的。
  - 历史记录文件仅存储在本地；如果需要清除数据，请删除这些文件。

## 许可证

Apache-2.0。详情请参阅 `LICENSE` 文件。

## 待办事项

  - [ ] 添加一个包含固定版本号的 `requirements.txt` 文件和锁定文件
  - [ ] 为本地开发添加可选的 `.env` 文件支持 (dotenv)
  - [ ] 针对缺失/无效 API 密钥及速率限制提供更友好的错误提示
  - [ ] UI 优化
  - [ ] 优化会话导入导出
  - [ ] 国际化(I18N)：支持中英双语界面切换