import streamlit as st
from openai import OpenAI
import datetime
import os
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 全局页面配置 ---
st.set_page_config(
    page_title="社区健康", 
    page_icon="🧡", 
    layout="centered", 
    initial_sidebar_state="collapsed" 
)

# --- 2. Google Sheets 连接配置 ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 【新增功能】获取用户 IP 地址
def get_user_ip():
    try:
        # Streamlit Cloud 会把真实 IP 放在 X-Forwarded-For 这个头部里
        # 如果是本地运行，可能获取不到，显示为 Localhost
        if st.context.headers:
            ip = st.context.headers.get("X-Forwarded-For")
            if ip:
                return ip.split(",")[0] # 有时候会有多个IP，取第一个
        return "Unknown/Local"
    except:
        return "Unknown"

# 【修改功能】增加 ip 参数
def save_to_google_sheet(role, content, ip):
    """
    尝试将数据写入 Google Sheets
    """
    if "gcp_service_account" not in st.secrets:
        return False

    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open("health_logs").sheet1
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 【修改点】写入4列：时间, IP, 角色, 内容
        sheet.append_row([timestamp, ip, role, content])
        return True
        
    except Exception as e:
        print(f"写入表格失败: {e}")
        return False

# --- 3. CSS 样式 (保持不变) ---
def inject_custom_css(font_size_mode):
    if font_size_mode == "👴 长辈版 (超大字)":
        st.markdown("""
            <style>
            html, body, [class*="css"] { font-size: 26px !important; font-weight: 500 !important; }
            h1 { font-size: 40px !important; color: #d9534f !important; }
            .stButton button {
                height: 3.5em !important; font-size: 24px !important;
                border-radius: 15px !important; background-color: #f0f2f6;
                border: 2px solid #d9534f; color: #333 !important;
            }
            div[role="radiogroup"] label { font-size: 22px !important; background-color: #fff9f9; padding: 10px; border-radius: 10px; }
            .stChatInput textarea { font-size: 24px !important; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            html, body, [class*="css"] { font-size: 18px !important; }
            .stButton button { border-radius: 8px !important; }
            </style>
        """, unsafe_allow_html=True)

# --- 4. 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "您好！我是您的专属运动指导员。💪"}
    ]

# --- 5. 顶部控制区 ---
st.title("🧡 社区健康指导员")

c1, c2 = st.columns([2, 1]) 
with c1:
    mode = st.radio("👀 选择字体大小：", ["📱 标准版", "👴 长辈版 (超大字)"], index=1, horizontal=True)
with c2:
    st.write("") 
    st.write("") 
    if st.button("🔄 重新开始"):
        st.session_state.messages = []
        st.rerun()

inject_custom_css(mode)

# --- 6. API 连接 ---
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = "sk-xxxxxxxx" 

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

# --- 7. 快捷提问区 ---
st.divider()
st.markdown("##### 👇 快速获取运动方案：")
col_a, col_b = st.columns(2)
user_trigger = None
with col_a:
    if st.button("🦵 膝盖疼"): user_trigger = "我的膝盖有点疼，平时上下楼梯不舒服，该怎么运动？"
    if st.button("💓 高血压"): user_trigger = "我有高血压，运动的时候要注意什么？"
with col_b:
    if st.button("📉 我想减肥"): user_trigger = "我最近胖了，想减肥，但我不想去健身房。"
    if st.button("📅 制定计划"): user_trigger = "请给我制定一个适合我的四周运动计划。"
st.divider()

# --- 8. 聊天历史 ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 9. 处理输入 ---
if prompt := st.chat_input("也可以在这里打字...") or user_trigger:
    input_text = user_trigger if user_trigger else prompt

    # 【新增】获取当前用户的 IP
    user_ip = get_user_ip()

    # A. 显示用户输入
    with st.chat_message("user"):
        st.markdown(input_text)
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    # -> 【修改】保存到 Google Sheet (传入 user_ip)
    save_to_google_sheet("User", input_text, user_ip)

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
            
            # -> 【修改】保存到 Google Sheet (传入 user_ip，AI的IP和用户一样即可)
            save_to_google_sheet("AI", full_response, user_ip)

        except Exception as e:
            st.error(f"网络连接出错: {e}")
            
    if user_trigger:
        st.rerun()
