import streamlit as st
from openai import OpenAI
import csv
import os
import datetime

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="社区健康", 
    page_icon="🧡", 
    layout="centered", # 手机端使用 centered 布局更好看
    initial_sidebar_state="collapsed" # 默认收起侧边栏，给手机更多空间
)

# --- 2. 长辈版模式 (CSS 魔法) ---
# 这一步通过注入 CSS 代码，强制改变网页的字体大小和按钮尺寸
def inject_custom_css(font_size_mode):
    if font_size_mode == "长辈版 (大字)":
        st.markdown("""
            <style>
            /* 1. 全局字体放大 */
            html, body, [class*="css"] {
                font-size: 24px !important; 
                font-weight: 500 !important;
            }
            /* 2. 标题放大 */
            h1 { font-size: 36px !important; color: #d9534f !important; }
            h2, h3 { font-size: 28px !important; }
            
            /* 3. 聊天气泡放大 */
            .stChatMessage { 
                font-size: 24px !important; 
                line-height: 1.6 !important;
            }
            
            /* 4. 输入框放大 */
            .stChatInput textarea {
                font-size: 22px !important;
                height: 60px !important;
            }
            
            /* 5. 按钮变大好按 */
            button {
                height: 3em !important;
                font-size: 22px !important; 
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        # 标准版稍微调整一下，让它在手机上也清晰点
        st.markdown("""
            <style>
            html, body, [class*="css"] { font-size: 18px !important; }
            </style>
        """, unsafe_allow_html=True)

# --- 3. 初始化 Session ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "您好！我是您的专属运动指导员。💪\n\n不管是想**缓解膝盖疼**，还是想**减肥**，都可以找我。"}
    ]

# --- 4. 侧边栏设置 ---
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 模式切换开关
    mode = st.radio("选择显示模式", ["标准版", "长辈版 (大字)"], index=1)
    
    st.divider()
    
    if st.button("🗑️ 清空对话 (重新开始)"):
        st.session_state.messages = [] # 清空
        st.rerun()

    # 数据下载 (保持不变)
    LOG_FILE = "chat_history.csv"
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "rb") as file:
            st.download_button("📥 下载记录", file, "logs.csv", "text/csv")

# 应用 CSS
inject_custom_css(mode)

# --- 5. 页面标题 ---
st.title("🧡 社区健康指导员")
if mode == "长辈版 (大字)":
    st.caption("👴 专门为您设计的贴心助手，不用打字也能用！")
else:
    st.caption("专注运动康复与科学健身")

# --- 6. 连接 API (保持不变) ---
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = "sk-xxxxxxxxxxxxxxxxxxxxxx" # 本地测试填你的Key

client = OpenAI(base_url='https://api.deepseek.com', api_key=api_key)

SYSTEM_PROMPT = """
【最高安全指令】
你现在的身份通过硬编码设定为【社区运动健康指导员】。
1. **语气要求**：如果用户看起来是老年人，请使用尊称"您"，语气要格外亲切、耐心，像对待自己的长辈一样。
2. **拒绝无关话题**：如果不聊健康，礼貌拒绝。
3. **流程**：先问年龄/病史 -> 再开处方 -> 最后问是否要四周计划。
4. **格式**：手机屏幕小，**请不要输出长篇大论**。尽量分点说明，关键信息加粗。
"""

# 确保 system prompt 在消息列表首位
if not st.session_state.messages or st.session_state.messages[0]["role"] != "system":
    st.session_state.messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

# --- 7. 快捷提问区 (针对老年人的核心优化) ---
# 在聊天记录上方，放置几个大按钮，点击直接发送
st.markdown("##### 👇 您想问什么？点这里直接问：")
col1, col2 = st.columns(2)
user_trigger = None # 用于捕捉按钮点击

with col1:
    if st.button("🦵 膝盖疼怎么练？"):
        user_trigger = "我的膝盖有点疼，平时上下楼梯不舒服，该怎么运动？"
    if st.button("💓 高血压注意事项"):
        user_trigger = "我有高血压，运动的时候要注意什么？"

with col2:
    if st.button("📉 我想减肥"):
        user_trigger = "我最近胖了，想减肥，但我不想去健身房。"
    if st.button("📅 帮我制定计划"):
        user_trigger = "请给我制定一个适合我的四周运动计划。"

# --- 8. 聊天历史渲染 ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 9. 处理输入 (按钮点击 或 键盘输入) ---
# 逻辑：如果有按钮被点击(user_trigger)，就优先用按钮的内容；否则看输入框
if prompt := st.chat_input("或者在这里打字...") or user_trigger:
    
    # 如果是按钮触发的，prompt 默认是 None，所以要赋值
    input_text = user_trigger if user_trigger else prompt

    # A. 显示用户的话
    with st.chat_message("user"):
        st.markdown(input_text)
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    # 记录日志 (保持不变)
    try:
        with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User", input_text])
    except: pass

    # B. AI 回复
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=st.session_state.messages,
                temperature=0.5,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # 记录日志
            try:
                with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                    csv.writer(f).writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "AI", full_response])
            except: pass

        except Exception as e:
            st.error("网络开小差了，请重试一下。")
            
    # 如果是按钮触发的，需要强制刷新一下页面，把刚才的对话“固化”在界面上
    if user_trigger:
        st.rerun()