import streamlit as st
from openai import OpenAI
import csv
import os
import datetime

# --- 1. 全局配置 (修复点：把文件名定义放在最前面) ---
LOG_FILE = "chat_history.csv" 

st.set_page_config(
    page_title="社区健康", 
    page_icon="🧡", 
    layout="centered", 
    initial_sidebar_state="collapsed" 
)

# --- 2. CSS 样式注入 (控制字号) ---
def inject_custom_css(font_size_mode):
    if font_size_mode == "👴 长辈版 (超大字)":
        st.markdown("""
            <style>
            html, body, [class*="css"] {
                font-size: 26px !important; 
                font-weight: 500 !important;
            }
            h1 { font-size: 40px !important; color: #d9534f !important; }
            
            .stButton button {
                height: 3.5em !important;
                font-size: 24px !important;
                border-radius: 15px !important;
                background-color: #f0f2f6;
                border: 2px solid #d9534f;
                color: #333 !important;
            }
            div[role="radiogroup"] label {
                font-size: 22px !important;
                background-color: #fff9f9;
                padding: 10px;
                border-radius: 10px;
            }
            .stChatInput textarea {
                font-size: 24px !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
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

# --- 4. 顶部控制区 ---
st.title("🧡 社区健康指导员")

c1, c2 = st.columns([2, 1]) 
with c1:
    mode = st.radio(
        "👀 选择字体大小：", 
        ["📱 标准版", "👴 长辈版 (超大字)"], 
        index=1, 
        horizontal=True
    )
with c2:
    st.write("") 
    st.write("") 
    if st.button("🔄 重新开始"):
        st.session_state.messages = []
        st.rerun()

inject_custom_css(mode)

# --- 5. 系统逻辑与API ---
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = "sk-xxxxxxxxxxxxxxxxxxxxxx" # 本地测试填你的Key

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

# --- 6. 快捷提问大按钮 ---
st.divider()
st.markdown("##### 👇哪怕不会打字，点下面也能问：")

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
    
    # 记录日志 (User)
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
            
            # 记录日志 (AI)
            try:
                with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                    csv.writer(f).writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "AI", full_response])
            except: pass

        except Exception as e:
            st.error("网络信号不太好，请重新点一下按钮。")
            
    if user_trigger:
        st.rerun()

# ... 前面的代码都不用动 ...

# --- 9. 带密码锁的后台入口 ---
with st.sidebar:
    st.divider()
    st.caption("🔒 管理员后台")
    
    # 1. 创建一个密码输入框
    # type="password" 会把输入的字变成圆点，防止被人偷看
    admin_pwd = st.text_input("请输入管理员密码", type="password")
    
    # 2. 从 Secrets 读取正确密码
    # 如果没配置 secrets (本地测试)，默认密码是 "admin"
    if "ADMIN_PASSWORD" in st.secrets:
        correct_pwd = st.secrets["ADMIN_PASSWORD"]
    else:
        correct_pwd = "admin"

    # 3. 校验密码
    if admin_pwd == correct_pwd:
        st.success("✅ 已验证")
        
        # 只有密码对的时候，才去读文件、显示按钮
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as file:
                st.download_button(
                    label="📥 点击下载所有数据 (CSV)",
                    data=file,
                    file_name=f"health_logs_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            # 增加一个显示数据条数的功能，让你心里有数
            try:
                with open(LOG_FILE, "r", encoding='utf-8-sig') as f:
                    row_count = sum(1 for row in f) - 1 # 减去表头
                st.caption(f"当前累计数据：{row_count} 条")
            except: pass
            
        else:
            st.warning("暂无数据记录")
    
    elif admin_pwd:
        # 如果密码输错了（且不是空的），提示错误
        st.error("❌ 密码错误")