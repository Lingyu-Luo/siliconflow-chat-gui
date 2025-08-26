import streamlit as st
from openai import OpenAI
import os
import json
import re
from datetime import datetime
import base64
import requests

# 配置基础信息
headers = {
    "Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}",
    "Content-Type": "application/json"
}

# 白名单处理混合推理
hybrid_model_list = [
    "deepseek-ai/DeepSeek-V3.1",
    "Pro/deepseek-ai/DeepSeek-V3.1",
    "zai-org/GLM-4.5V"
]

def make_payload(model: str, messages: list, enable_thinking: bool | None = None, stream: bool = True):
    # 构建请求负载
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": st.session_state.max_tokens,
        "temperature": st.session_state.temperature,
        "top_p": st.session_state.top_p,
        "stream": stream
    }

    if enable_thinking is not None and model in hybrid_model_list:
        payload["enable_thinking"] = enable_thinking

    return payload

HISTORY_DIR = "ChatHistory"
MEMORY_FILE = "memories.json"
NUM_CONVO_DISPLAY = 10
os.makedirs(HISTORY_DIR, exist_ok=True)
base_url = "https://api.siliconflow.cn/v1/chat/completions"
name_model = "deepseek-ai/DeepSeek-V3.1"
vlm_model = "zai-org/GLM-4.5V"
vlm_max_tokens = "8192"

def init_session():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_convo' not in st.session_state:
        st.session_state.current_convo = None
    if 'convo_list' not in st.session_state:
        st.session_state.convo_list = []
    if 'num_convo_display' not in st.session_state:
        st.session_state.num_convo_display = 10
    # 新增模型参数初始化
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "deepseek-ai/DeepSeek-R1"
    if 'max_tokens' not in st.session_state:
        st.session_state.max_tokens = 2048
    if 'temperature' not in st.session_state:
        st.session_state.temperature = 1.0
    if 'top_p' not in st.session_state:
        st.session_state.top_p = 1.0

    # 历史记录兼容（处理多模态消息）
    for msg in st.session_state.get('messages', []):
        if isinstance(msg.get("content"), list):
            for item in msg["content"]:
                if item["type"] == "image_url":
                    item["image_url"]["url"] = str(item["image_url"]["url"])

def generate_filename(content):
    # 提取文本内容用于生成文件名
    text_content = ""
    if isinstance(content, list):
        texts = [item["text"] for item in content if isinstance(item, dict) and item.get("type") == "text"]
        text_content = " ".join(texts)
    else:
        text_content = str(content)
    
    messages=[
            {"role": "system", "content": "你是一个对话命名助手，帮助提取对话关键词作为对话记录文件名，十五字以内。"},
            {"role": "user", "content": "提取对话的主题（仅输出主题本身）：" + text_content}
        ]
    response = requests.post(base_url, json=make_payload(name_model,messages,enable_thinking=False,stream=False), headers=headers)

    clean_content = (response.json())["choices"][0]["message"].get("content", "").strip()

    clean_content = re.sub(r'[\n\r\t\\/*?:"<>|]', "", clean_content)[:15]
    timestamp = datetime.now().strftime("%m%d%H%M")
    return f"{timestamp}_{clean_content}.json" if clean_content else f"{timestamp}_未命名.json"

def convert_messages_for_api(messages, use_vlm):
    """转换消息格式适配不同模型"""
    converted = []
    for msg in messages:
        if use_vlm:
            if isinstance(msg["content"], list):
                content = []
                for item in msg["content"]:
                    if item["type"] in ["text", "image_url"]:  # 只保留这两种类型
                        content_item = {"type": item["type"]}
                        if item["type"] == "image_url":
                            content_item["image_url"] = {"url": item["image_url"]["url"]}
                        elif item["type"] == "text":
                            content_item["text"] = item.get("text", "")
                        content.append(content_item)
            else:
                content = [{"type": "text", "text": str(msg["content"])}]
        else:
            if isinstance(msg["content"], list):
                ref_text = ""
                content = ""
                for item in msg["content"]:
                    if item.get("type") == "reference":
                        ref_text = "\n\n【相关参考资料】\n"
                        for i,ref in enumerate(item.get("reference",[])):
                            ref_text += f"{i + 1}. {ref.get('content','')[:4096]}\n\n来源：{ref.get('title','无标题')} ({ref.get('link','无链接')})\n\n"
                if ref_text:
                    content = ref_text +"原输入：\n"
                text_parts = [item["text"] for item in msg["content"] if item.get("type") == "text"]
                content += " ".join(text_parts)
            else:
                content = msg["content"]
        converted.append({"role": msg["role"], "content": content})
    return converted

def refresh_convo_list():
    st.session_state.convo_list = [
        f for f in os.listdir(HISTORY_DIR)
        if f.endswith('.json') and os.path.getsize(os.path.join(HISTORY_DIR, f)) > 0
    ]
    st.session_state.convo_list.reverse()


def new_conversation():
    st.session_state.messages = []
    st.session_state.current_convo = None


def load_conversation(filename):
    path = os.path.join(HISTORY_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        st.session_state.messages = json.load(f)
    st.session_state.current_convo = filename

def save_conversation():
    if st.session_state.current_convo and st.session_state.messages:
        path = os.path.join(HISTORY_DIR, st.session_state.current_convo)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)


def render_with_latex(text: str):
    text = text.replace(r'\\\\',r"\\")
    text = text.replace(r'\(',r"$")
    text = text.replace(r'\)', r"$")
    text = text.replace(r'\[', r"$$")
    text = text.replace(r'\]', r"$$")
    st.markdown(text)

# 初始化会话
init_session()

# 侧边栏布局
with st.sidebar:
    st.title("对话管理")

    # 新增模型设置区域
    st.subheader("模型设置")

    st.session_state.enable_web_search = st.checkbox(
        "启用网络搜索 (web_search)",
        value=st.session_state.get("enable_web_search", False),
        help="启用网络搜索增强回答准确性"
    )

    st.session_state.selected_model = st.selectbox(
        "选择对话模型",
        ["deepseek-ai/DeepSeek-V3.1",
         "Qwen/Qwen3-235B-A22B-Thinking-2507",
         "zai-org/GLM-4.5",
         "Pro/deepseek-ai/DeepSeek-V3.1"],
        index=0
    )

    # 参数调节部分
    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.max_tokens = st.slider(
            "最大生成长度 (max_tokens)",
            1024, 16384, 8192,
            help="控制生成内容的最大长度"
        )
    with col2:
        st.session_state.max_tokens = st.number_input(
            "输入值",
            min_value=1024,
            max_value=16384,
            value=8192,
            step=128,
            key="max_tokens_input"
        )

    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.temperature = st.slider(
            "创造性 (temperature)",
            0.0, 2.0, 0.6, 0.1,
            help="值越大生成内容越随机"
        )
    with col2:
        st.session_state.temperature = st.number_input(
            "输入值",
            min_value=0.0,
            max_value=2.0,
            value=0.6,
            step=0.1,
            key="temp_input",
            format="%.1f"
        )

    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.top_p = st.slider(
            "核心采样 (top_p)",
            0.0, 1.0, 0.95, 0.01,
            help="控制生成内容的多样性"
        )
    with col2:
        st.session_state.top_p = st.number_input(
            "输入值",
            min_value=0.0,
            max_value=1.0,
            value=0.95,
            step=0.01,
            key="top_p_input",
            format="%.2f"
        )

    if st.button("➕ 新建对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_convo = None
        st.rerun()

    st.subheader("历史对话")
    refresh_convo_list()
    convo_render_list = st.session_state.convo_list[:st.session_state.num_convo_display]
    for convo in convo_render_list:
        cols = st.columns([3, 1])
        with cols[0]:
            if st.button(convo[:-5], key=f"btn_{convo}", use_container_width=True):
                load_conversation(convo)
                st.rerun()
        with cols[1]:
            if st.button("×", key=f"del_{convo}", type='primary'):
                os.remove(os.path.join(HISTORY_DIR, convo))
                if st.session_state.current_convo == convo:
                    new_conversation()
                st.rerun()
    if st.session_state.num_convo_display < len(st.session_state.convo_list):
        if st.button("加载更多...",key="load_more_convo"):
            st.session_state.num_convo_display += 10
            st.rerun()

# 主界面布局
st.title("智能对话助手（支持图文）")

# 显示聊天记录（支持多模态）
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        # 先显示推理内容（如果有）
        if msg["role"] == "assistant" and msg.get("reasoning"):
            with st.expander("🧠 推理过程（点击展开）"):
                render_with_latex(msg["reasoning"])

        # 再显示消息内容
        if isinstance(msg["content"], list):
            for item in msg["content"]:
                if item["type"] == "image_url":
                    try:
                        base64_str = item["image_url"]["url"].split(",")[1]
                        st.image(base64.b64decode(base64_str), use_container_width=True)
                    except:
                        st.error("图片加载失败")
                elif item["type"] == "text" and item["text"].strip():
                    render_with_latex(item["text"])
                elif item["type"] == "reference":
                    with st.expander("📚 参考来源（点击展开）"):
                        for i, ref in enumerate(item["reference"]):
                            st.caption(f"参考资料 {i + 1}")
                            render_with_latex(f"```\n{ref['content']}\n```")
                            if 'title' and 'link' in ref:
                                st.caption(f"{ref['title']}\n{ref['link']}")
        else:
            render_with_latex(msg["content"])

# 处理用户输入（新增图片上传）
uploaded_files = st.file_uploader(
    "📤 上传图片（支持多选）",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="file_uploader"
)

if prompt := st.chat_input("请输入您的问题或描述..."):
    # 构建多模态消息内容
    message_content = []

    # 处理上传的图片
    for uploaded_file in uploaded_files:
        if uploaded_file:
            base64_str = base64.b64encode(uploaded_file.read()).decode("utf-8")
            mime_type = uploaded_file.type
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_str}"
                }
            })
            uploaded_file.seek(0)  # 重置文件指针

    # 处理文本输入
    if prompt.strip():
        message_content.append({
            "type": "text",
            "text": prompt.strip()
        })

    references = []

    # WEB_SEARCH 搜索 (deprecated)
    # if st.session_state.enable_web_search and not len(message_content) > 1:

    # 保存用户消息
    user_message = {
        "role": "user",
        "content": message_content if len(message_content) > 1 else prompt
    }
    st.session_state.messages.append(user_message)

    # 显示用户消息
    with st.chat_message("user", avatar="🧑"):
        for item in message_content:
            if item["type"] == "image_url":
                try:
                    base64_str = item["image_url"]["url"].split(",")[1]
                    st.image(base64.b64decode(base64_str), use_container_width=True)
                except:
                    st.error("图片显示失败")
            elif item["type"] == "text":
                render_with_latex(item["text"])
            elif item["type"] == "reference":
                with st.expander("📚 参考来源（点击展开）"):
                    for i, ref in enumerate(item["reference"]):
                        st.caption(f"参考资料 {i + 1}")
                        render_with_latex(f"```\n{ref['content']}\n```")
                        if 'title' and 'link' in ref:
                            st.caption(f"{ref['title']}\n{ref['link']}")


    # 自动选择模型
    use_vlm = any(
        isinstance(msg.get("content"), list) and
        any(item.get("type") == "image_url" for item in msg.get("content", []))
        for msg in st.session_state.messages[-1:]
    )

    # 准备API请求
    try:
        with ((st.chat_message("assistant", avatar="🤖️"))):
            reasoning_placeholder = st.empty()
            answer_placeholder = st.empty()
            full_reasoning = ""
            full_answer = ""

            # 转换消息格式
            api_messages = convert_messages_for_api(st.session_state.messages, use_vlm)

            # 创建API请求
            print("正在发送api请求...")
            response = requests.post(base_url, json=make_payload(model= vlm_model if use_vlm else st.session_state.selected_model, messages=api_messages, enable_thinking = True if st.session_state.selected_model in hybrid_model_list else None), headers=headers, stream=True) # 指定stream模式

            # 处理流式响应
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8').replace('data: ', '')
                    if chunk_str != "[DONE]":
                        try:
                            chunk_data = json.loads(chunk_str)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk_data.get('choices', [{}])[0].get('delta', {})
                        content = delta.get('content', '')
                        reasoning_content = delta.get('reasoning_content', '')
                        if content:
                            full_answer += content
                            with answer_placeholder:
                                render_with_latex(full_answer + "▌")
                        if reasoning_content:
                            full_reasoning += reasoning_content
                            if full_reasoning.strip():
                                with reasoning_placeholder.expander("🤔 实时推理"):
                                    render_with_latex(full_reasoning)
            print("响应接受完成。")

            # 保存最终响应
            with reasoning_placeholder:
                if full_reasoning.strip():
                    with st.expander("🧠 推理过程"):
                        render_with_latex(full_reasoning.strip())
            with answer_placeholder:
                render_with_latex(full_answer)
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_answer,
                "reasoning": full_reasoning.strip()
            })

    except Exception as e:
        st.error(f"请求失败: {str(e)}")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "响应生成失败",
            "reasoning": f"错误信息: {str(e)}"
        })

    # 生成文件名（优先使用文本内容）
    filename_content = prompt.strip()
    if not st.session_state.current_convo:
        print("正在生成对话文件名...")
        st.session_state.current_convo = generate_filename(filename_content)
    # 保存对话记录
    if st.session_state.current_convo:
        save_conversation()
        refresh_convo_list()
    print("\n")

# 自动滚动和保存功能（保持不变）
st.markdown("""
<script>
// 自动滚动到底部
window.addEventListener('DOMContentLoaded', () => {
    const scrollToBottom = () => {
        window.scrollTo(0, document.body.scrollHeight);
    };
    scrollToBottom();
});
</script>
""", unsafe_allow_html=True)