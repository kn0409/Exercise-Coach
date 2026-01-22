import streamlit as st
from openai import OpenAI
import csv
import os
import datetime

# --- 1. 全局配置 ---
# 定义日志文件名 (放在最前面防止报错)
LOG_FILE = "chat_history.csv" 

st.set_page_config(
    page_title="社区健康", 
    page_icon="🧡", 
    layout="centered", 
    initial_sidebar_state="collapsed" 
)

# --- 2. CSS 样式注入 (控制字号与按钮) ---
def inject_custom_css(font_size_mode):
    if font_size_mode == "👴 长辈版 (超大字)":
        st.markdown("""
            <style>
            /* 全局放大 */
            html, body, [class*="css"] {
                font-size: 26px !important; 
                font-weight: 500 !important;
            }
            h1 { font-size: 40px !important; color: #d9534f !important; }
            
            /* 按钮美化：大尺寸 + 红边框 */
            .stButton button {
                height: 3.5em !important;
                font-size: 24px !important;
                border-radius: 15px !important;
                background-color: #fff;
                border: 2px solid #d9534f;
                color: #333 !important;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
            }
            /* 单选框样式 */
            div[role="radiogroup"] label {
                font-size: 22px !important;
                background-color: #fff9f9;
                padding: 10px;
                border-radius: 10px;
                margin-right: 10px;
            }
            /* 输入框放大 */
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

# --- 4. 顶部控制区 (UI) ---
st.title("🧡 社区健康指导员")

# 布局：左边选模式，右边重置
c1, c2 = st.columns([7, 3]) 
with c1:
    mode = st.radio(
        "👀 字体模式：", 
        ["📱 标准", "👴 长辈版"], 
        index=1, 
        horizontal=True,
        label_visibility="collapsed" # 隐藏标签让界面更清爽
    )
with c2:
    st.write("") # 占位
    if st.button("🔄 重置"):
        st.session_state.messages = []
        st.rerun()

# 应用 CSS
inject_custom_css(mode)

# --- 5. 连接 DeepSeek API ---
# 优先从 Secrets 读取 Key，如果没有则用占位符
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = "sk-xxxxxxxxxxxxxxxxxxxxxx" # 本地测试时填你的Key

client = OpenAI(base_url='https://api.deepseek.com', api_key=api_key)

# --- 6. 系统提示词 (大脑设定) ---
SYSTEM_PROMPT = """
【最高安全指令】
你现在的身份通过硬编码设定为【社区运动健康指导员】。
1. **对象感知**：如果用户使用快捷按钮或语气像老年人，请务必使用尊称"您"，语气亲切、耐心，像对待长辈一样。
2. **拒绝无关话题**：如果不聊健康/运动/身体，请礼貌拒绝："不好意思，我只懂健康方面的事儿。"
3. **工作流程**：
   - 先询问：哪里不舒服？多大年纪？
   - 再建议：给出安全的运动建议。
   - 后规划：询问是否需要制定【四周计划】。
4. **输出限制**：手机屏幕小，**回答必须精简**，不要长篇大论。重点信息加粗。
"""

# 确保 Prompt 始终在第一条
if not st.session_state.messages or st.session_state.messages[0]["role"] != "system":
    st.session_state.messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

# --- 7. 快捷提问区 (大按钮) ---
st.divider()
st.caption("👇 点下面直接问：")

col_a, col_b = st.columns(2)
user_trigger = None

with col_a:
    if st.button("🦵 膝盖疼"):
        user_trigger = "我的膝盖有点疼，上下楼梯不舒服，该怎么运动？"
    if st.button("💓 高血压"):
        user_trigger = "我有高血压，平时运动要注意什么？"

with col_b:
    if st.button("📉 想减肥"):
        user_trigger = "我最近胖了，想减肥，但我不想去健身房，就在家练。"
    if st.button("📅 定计划"):
        user_trigger = "请给我制定一个适合我的【四周运动计划】，要循序渐进的。"

st.divider()

# --- 8. 聊天记录渲染 ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 9. 处理核心逻辑 ---
# 无论是按钮触发 还是 键盘输入，都走这里
if prompt := st.chat_input("也可以在这里输入...") or user_trigger:
    
    input_text = user_trigger if user_trigger else prompt

    # A. 显示用户输入
    with st.chat_message("user"):
        st.markdown(input_text)
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    # 记录 CSV (User)
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
            
            # 记录 CSV (AI)
            try:
                with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                    csv.writer(f).writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "AI", full_response])
            except: pass

        except Exception as e:
            st.error("哎呀，网络有点卡，请您再点一下按钮。")
            
    # 如果是按钮触发，强制刷新页面以锁定状态
    if user_trigger:
        st.rerun()

# --- 10. 管理员后台 (带密码锁) ---
with st.sidebar:
    st.divider()
    st.caption("🔒 管理员后台")
    
    # 密码框
    admin_pwd = st.text_input("输入密码下载数据", type="password")
    
    # 获取正确密码 (如果在 secrets 里配置了就用配置的，否则默认 admin)
    if "ADMIN_PASSWORD" in st.secrets:
        correct_pwd = st.secrets["ADMIN_PASSWORD"]
    else:
        correct_pwd = "admin" # 本地测试默认密码

    if admin_pwd == correct_pwd:
        st.success("验证通过")
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as file:
                st.download_button(
                    label="📥 下载所有数据 (CSV)",
                    data=file,
                    file_name=f"health_logs_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            # 显示数据量
            try:
                with open(LOG_FILE, "r", encoding='utf-8-sig') as f:
                    count = sum(1 for row in f) - 1
                st.info(f"当前累计：{count} 条对话")
            except: pass
        else:
            st.warning("暂无数据")
    elif admin_pwd:
        st.error("密码错误")