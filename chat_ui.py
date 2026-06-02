import streamlit as st
import requests
import uuid

st.set_page_config(page_title="AgentOS Chat Interface", page_icon="🤖")

# --- Configuration ---
API_URL = "http://localhost:8000/chat"
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🤖 AgentOS AI Assistant")

with st.sidebar:
    st.header("⚙️ Connection Settings")
    api_url = st.text_input("API Server URL", value="http://localhost:8000/chat")
    
    st.divider()
    
    st.subheader("Session Management")
    session_id = st.text_input("Session ID", value=st.session_state.session_id)
    if st.button("🔄 Generate New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

st.caption(f"Session ID: {st.session_state.session_id}")

# แสดงประวัติการแชท
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ช่องกรอกข้อมูล UI Chat
if prompt := st.chat_input("พิมพ์คำสั่งหรือคำถามที่นี่..."):
    # แสดงข้อความของผู้ใช้
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # เรียกใช้ AgentOS API
    with st.chat_message("assistant"):
        with st.spinner("Agent กำลังประมวลผล..."):
            try:
                response = requests.post(
                    api_url, 
                    json={"session_id": session_id, "message": prompt},
                    timeout=120
                )
                if response.status_code == 200:
                    answer = response.json().get("answer", "ไม่มีคำตอบกลับมา")
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"API Error: {response.status_code}")
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")
