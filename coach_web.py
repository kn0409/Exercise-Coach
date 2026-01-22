import streamlit as st
from openai import OpenAI
import csv
import os
import datetime

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="社区健康", 
    page_icon="🧡", 
    layout="centered", 
    initial_sidebar_state="collapsed" 
)

# --- 2. CSS 样式注入 (核心：控制字号) ---
def inject_custom_css(font_size_mode):
    if font_size_mode == "👴 长辈版 (超大字)":
        st.markdown("""
            <style>
            /* 全局放大 */
            html, body, [class*="css"] {
                font-size: 26px !important; 
                font-weight: 500 !important;
            }
            /* 标题特别大 */
            h1 { font-size: 40px !important; color: #d9534f !important; }
            
            /* 按钮变得非常易按 */
            .stButton button {
                height: 3.5em !important;
                font-size: 24px !important;
                border-radius: 15px !important; /* 圆角更友好 */
                background-color: #f0f2f6;
                border: 2px solid #d9534f; /* 加个红边框更明显 */
                color: #333 !important;
            }
            /* 选中状态的单选框 */
            div[role="radiogroup"] label {
                font-size: 22px !important;
                background-color: #fff9f9;
                padding: 10px;
                border-radius: 10px;
            }
            
            /* 输入框 */
            .stChatInput textarea {
                font-size: 24px !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        # 标准版
        st.markdown("""
            <style>
            html, body, [class*="css"] { font-size: 18px !important; }
            .stButton button { border-radius: 8px !important; }
            </style>
        """, unsafe_allow_html=True)

# --- 3. 初始化 Session ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "您好！我是您的专属运动指导员。💪"}
    ]

# --- 4. 顶部控制区 (UI重构：移到主页) ---
st.title("🧡 社区健康指导员")

# 使用两列布局：左边选模式，右边清空
c1, c2 = st.columns([2, 1]) 

with c1:
    # horizontal=True 让选项横着排，不占地方
    mode = st.radio(
        "👀 选择字体大小：", 
        ["📱 标准版", "👴 长辈版 (超大字)"], 
        index=1, 
        horizontal=True
    )

with c2:
    # 做一个空的间隔，让按钮对齐下去一点
    st.write("") 
    st.write("") 
    if st.button("🔄 重新开始"):
        st.session_state.messages = []
        st.rerun()

# 立即应用 CSS
inject_custom_css(mode)

# --- 5. 系统逻辑与API ---
# 如果使用了 secrets (云端)，否则用本地 key
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = "sk-xxxxxxxxxxxxxxxxxxx" # 本地测试填你的Key

client = OpenAI(base_url='https://api.deepseek.com', api_key=api_key)

SYSTEM_PROMPT = """
【最高安全指令】
你现在的身份通过硬编码设定为【社区运动健康指导员】。
1. **语气要求**：使用尊称"您"，语气亲切、耐心。
2. **拒绝无关话题**：如果不聊健康，礼貌拒绝。
3. **流程**：先问年龄/病史 -> 再开处方 -> 最后问是否要四周计划。
4. **格式**：手机屏幕小，**请不要输出长篇大论**。尽量分点说明，关键信息加粗。
"""

if not st.session_state.messages or st.session_state.messages[0]["role"] != "system":
    st.session_state.messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

# --- 6. 快捷提问大按钮 (核心交互区) ---
st.divider()
st.markdown("##### 👇哪怕不会打字，点下面也能问：")

# 按钮矩阵
col_a, col_b = st.columns(2)
user_trigger = None

with col_a:
    if st.button("🦵 膝盖疼"):
        user_trigger = "我的膝盖有点疼，平时上下楼梯不舒服，该怎么运动？"
    if st.button("💓 高血压"):
        user_trigger = "我有高血压，运动的时候要注意什么？"

with col_b:
    if st.button("📉 我想减肥"):
        user_trigger = "我最近胖了，想减肥，但我不想去健身房。"
    if st.button("📅 制定计划"):
        user_trigger = "请给我制定一个适合我的四周运动计划。"

st.divider()

# --- 7. 聊天记录显示 ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 8. 处理输入 ---
if prompt := st.chat_input("也可以在这里打字...") or user_trigger:
    
    input_text = user_trigger if user_trigger else prompt

    # A. 显示用户输入
    with st.chat_message("user"):
        st.markdown(input_text)
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    # 记录日志
    LOG_FILE = "chat_history.csv"
    try:
        with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User", input_text])
    except: pass

    # B. AI 生成回复
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
            
            try:
                with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                    csv.writer(f).writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "AI", full_response])
            except: pass

        except Exception as e:
            st.error("网络信号不太好，请重新点一下按钮。")
            
    # 按钮触发后刷新页面，防止状态卡住
    if user_trigger:
        st.rerun()

# --- 9. 隐藏式后台入口 ---
# 只有把页面拉到最最底下，展开侧边栏才能下载数据
# 防止老人误触
with st.sidebar:
    st.caption("🔒 管理员后台")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "rb") as file:
            st.download_button("📥 导出数据 CSV", file, "logs.csv", "text/csv")