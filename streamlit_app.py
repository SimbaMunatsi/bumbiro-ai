import os
import time
import uuid
import json
from typing import Any

import requests
import streamlit as st


st.set_page_config(
    page_title="BUMBIRO AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_URL = os.getenv("API_URL", "http://localhost:8000")


def init_session_state() -> None:
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "api_url" not in st.session_state:
        st.session_state.api_url = API_URL
    if "show_sources" not in st.session_state:
        st.session_state.show_sources = True
    if "backend_status" not in st.session_state:
        st.session_state.backend_status = False
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "current_sources" not in st.session_state:
        st.session_state.current_sources = []


def wait_for_backend() -> None:
    if st.session_state.backend_status is True:
        return
    backend_ready = False
    with st.spinner("🚀 Waking up the backend server... This usually takes 30-60 seconds."):
        for i in range(20): 
            try:
                response = requests.get(f"{API_URL}/health", timeout=5)
                if response.status_code == 200:
                    backend_ready = True
                    break
            except requests.exceptions.ConnectionError:
                time.sleep(3) 
    if not backend_ready:
        st.error("The backend is taking longer than usual to start. Please refresh the page.")
        st.stop()
    else:
        st.session_state.backend_status = True


# --- Authentication ---
def api_login(api_url: str, email: str, password: str) -> tuple[bool, str]:
    try:
        response = requests.post(
            f"{api_url}/auth/login",
            data={"username": email, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            st.session_state.access_token = token
            st.session_state.is_authenticated = True
            return True, "Login successful!"
        return False, response.json().get("detail", "Invalid credentials.")
    except Exception as e:
        return False, f"Connection error: {e}"


def api_register(api_url: str, email: str, password: str) -> tuple[bool, str]:
    try:
        response = requests.post(
            f"{api_url}/auth/register",
            json={"email": email, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "Registration successful!"
        return False, response.json().get("detail", "Registration failed.")
    except Exception as e:
        return False, f"Connection error: {e}"


def logout() -> None:
    st.session_state.is_authenticated = False
    st.session_state.access_token = None
    st.session_state.messages = []


# --- Chat API Call (Streaming) ---
def stream_query_api(api_url: str, query: str, session_id: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{api_url}/query-stream",
        json={"query": query, "session_id": session_id},
        headers=headers,
        timeout=120,
        stream=True 
    )
    if response.status_code == 401:
        logout()
        st.rerun()
    response.raise_for_status()
    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            if data["type"] == "chunk":
                yield data["content"]
            elif data["type"] == "sources":
                st.session_state.current_sources = data["content"]


# --- UI Components ---
def render_sources(sources: list[str]) -> None:
    if not sources or not st.session_state.show_sources:
        return
    with st.expander("Sources", expanded=False):
        for idx, source in enumerate(sources, start=1):
            st.markdown(f"**Source {idx}**")
            st.write(source)
            if idx < len(sources): st.markdown("---")


def handle_query(user_query: str) -> None:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        st.session_state.current_sources = []
        
        # 1. Show a 'Thinking' status while the backend is retrieving
        with st.status("⚖️ BumbiroAI is analyzing the Constitution...", expanded=True) as status:
            st.write("Retrieving relevant sections from Supabase...")
            st.write("Consulting BM25 keyword index...")
            
            try:
                stream_generator = stream_query_api(
                    api_url=st.session_state.api_url,
                    query=user_query,
                    session_id=st.session_state.session_id,
                    token=st.session_state.access_token, 
                )
                
                # We start the stream. write_stream will consume the generator.
                # The first token arrival will effectively end the 'waiting' phase.
                status.update(label="Found relevant information! Generating answer...", state="running")
                
                full_answer = st.write_stream(stream_generator)
                status.update(label="Analysis complete.", state="complete", expanded=False)

                sources = st.session_state.current_sources
                render_sources(sources)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_answer,
                    "sources": sources,
                })

            except Exception as exc:
                status.update(label="Error occurred.", state="error")
                st.error(f"Error: {exc}")


# --- Rest of UI (Condensed for brevity) ---
def render_auth_page() -> None:
    st.markdown("<h1 style='text-align: center;'>⚖️ BUMBIRO AI</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        with st.form("login_form"):
            e = st.text_input("Email"); p = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                s, m = api_login(st.session_state.api_url, e, p)
                if s: st.rerun()
                else: st.error(m)
    with tab2:
        with st.form("register_form"):
            e = st.text_input("Email "); p = st.text_input("Password ", type="password")
            if st.form_submit_button("Register"):
                s, m = api_register(st.session_state.api_url, e, p)
                if s: st.success(m)
                else: st.error(m)

def render_sidebar():
    with st.sidebar:
        st.markdown("## ZIM Constitution AI")
        if st.button("New chat"): st.session_state.messages = []; st.rerun()
        st.session_state.show_sources = st.toggle("Show sources", value=True)
        if st.button("Logout"): logout(); st.rerun()

def main():
    init_session_state()
    wait_for_backend()
    if not st.session_state.is_authenticated:
        render_auth_page()
        return
    render_sidebar()
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant": render_sources(m.get("sources", []))
    
    if prompt := st.chat_input("Ask about the Zimbabwe Constitution"):
        handle_query(prompt)

if __name__ == "__main__":
    main()