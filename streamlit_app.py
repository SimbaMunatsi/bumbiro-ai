import os
import time
import uuid
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
    # --- Auth States ---
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    # --- Chat States ---
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


def wait_for_backend() -> None:
    """Check if backend is alive, if not, wait and show a spinner."""
    # Skip the check if we already know the backend is awake for this session
    if st.session_state.backend_status is True:
        return

    backend_ready = False
    with st.spinner("🚀 Waking up the backend server... This usually takes 30-60 seconds."):
        # Try up to 20 times (approx 1 minute)
        for i in range(20): 
            try:
                # Ping the health endpoint using the global API_URL
                response = requests.get(f"{API_URL}/health", timeout=5)
                if response.status_code == 200:
                    backend_ready = True
                    break
            except requests.exceptions.ConnectionError:
                time.sleep(3) # Wait 3 seconds before retrying
    
    if not backend_ready:
        st.error("The backend is taking longer than usual to start. Please refresh the page.")
        st.stop()
    else:
        # Mark as ready so we don't run this check on every Streamlit UI interaction
        st.session_state.backend_status = True


# --- Authentication API Calls ---
def api_register(api_url: str, email: str, password: str) -> tuple[bool, str]:
    try:
        response = requests.post(
            f"{api_url}/auth/register",
            json={"email": email, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "Registration successful! You can now log in."
        else:
            return False, response.json().get("detail", "Registration failed.")
    except Exception as e:
        return False, f"Connection error: {e}"


def api_login(api_url: str, email: str, password: str) -> tuple[bool, str]:
    try:
        # OAuth2 strictly requires form data with 'username' and 'password'
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
        else:
            return False, response.json().get("detail", "Invalid credentials.")
    except Exception as e:
        return False, f"Connection error: {e}"


def logout() -> None:
    st.session_state.is_authenticated = False
    st.session_state.access_token = None
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())


# --- Chat API Call ---
def call_query_api(api_url: str, query: str, session_id: str, token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{api_url}/query",
        json={"query": query, "session_id": session_id},
        headers=headers,
        timeout=120,
    )
    if response.status_code == 401:
        # Token expired or invalid
        logout()
        st.rerun()
        
    response.raise_for_status()
    return response.json()


# --- UI Components ---
def clear_chat() -> None:
    st.session_state.messages = []


def new_chat() -> None:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []


def queue_prompt(prompt: str) -> None:
    st.session_state.pending_prompt = prompt


def render_auth_page() -> None:
    st.markdown(
        """
        <div style='text-align: center; margin-top: 50px;'>
            <h1 style='font-size: 3rem;'>⚖️ BUMBIRO AI</h1>
            <p style='color: #9aa0a6; font-size: 1.2rem;'>Secure login required to access the Zimbabwe Constitution AI.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            with st.form("login_form"):
                login_email = st.text_input("Email")
                login_password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Log In", use_container_width=True)

                if login_submitted:
                    if not login_email or not login_password:
                        st.error("Please fill in both fields.")
                    else:
                        with st.spinner("Authenticating..."):
                            success, msg = api_login(st.session_state.api_url, login_email, login_password)
                            if success:
                                st.rerun()
                            else:
                                st.error(msg)

        with tab2:
            with st.form("register_form"):
                reg_email = st.text_input("Email ")
                reg_password = st.text_input("Password ", type="password")
                reg_submitted = st.form_submit_button("Register", use_container_width=True)

                if reg_submitted:
                    if not reg_email or not reg_password:
                        st.error("Please fill in both fields.")
                    else:
                        with st.spinner("Creating account..."):
                            success, msg = api_register(st.session_state.api_url, reg_email, reg_password)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## ZIM Constitution AI Assistant")

        if st.button("New chat", use_container_width=True):
            new_chat()
            st.rerun()

        if st.button("Clear messages", use_container_width=True):
            clear_chat()
            st.rerun()

        st.markdown("### Preferences")
        st.session_state.show_sources = st.toggle(
            "Show sources",
            value=st.session_state.show_sources,
        )

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()


def render_header() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 900px;
        }
        .app-title {
            font-size: 2.4rem;
            font-weight: 700;
            margin-top: 1.2rem;
        }
        .app-subtitle {
            color: #9aa0a6;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }
        .empty-state {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 1.2rem 1.2rem 0.8rem 1.2rem;
            margin-top: 1rem;
            margin-bottom: 1rem;
            background: rgba(255,255,255,0.02);
        }
        </style>
        <div class="app-title">⚖️ BUMBIRO AI</div>
        <div class="app-subtitle">Learn about the Zimbabwe Constitution</div>
        """,
        unsafe_allow_html=True,
    )


def render_welcome_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
            <p style="margin-bottom: 0.4rem;">
                Ask questions about the Zimbabwe Constitution.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    suggestions = [
        "What is the Constitution of Zimbabwe? Discuss the process for amending it.",
        "Evaluate the mechanisms for accountability and oversight of the security service",
        "How does the Zimbabwe Constitution address the separation of powers?",
        "Differentiate between the Constitutional Court and the Supreme Court.",
    ]

    for i, prompt in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(prompt, use_container_width=True):
                queue_prompt(prompt)
                st.rerun()


def render_sources(sources: list[str]) -> None:
    if not sources or not st.session_state.show_sources:
        return

    with st.expander("Sources", expanded=False):
        for idx, source in enumerate(sources, start=1):
            st.markdown(f"**Source {idx}**")
            st.write(source)
            if idx < len(sources):
                st.markdown("---")


def render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources", []))


def handle_query(user_query: str) -> None:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        try:
            with st.spinner("Thinking..."):
                result = call_query_api(
                    api_url=st.session_state.api_url,
                    query=user_query,
                    session_id=st.session_state.session_id,
                    token=st.session_state.access_token, # Send the auth token
                )

            answer = str(result.get("answer", "")).strip()
            sources = result.get("sources", [])

            if not isinstance(sources, list):
                sources = [str(sources)]

            if not answer:
                answer = "No answer was returned by the backend."

            response_placeholder.markdown(answer)
            render_sources(sources)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                }
            )

        except requests.exceptions.HTTPError as exc:
            error_message = f"API error: {exc}"
            response_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})

        except requests.exceptions.RequestException as exc:
            error_message = f"Connection error: {exc}"
            response_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})

        except Exception as exc:
            error_message = f"Unexpected error: {exc}"
            response_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})


def main() -> None:
    init_session_state()
    
    # Check if backend is awake before allowing interactions
    wait_for_backend()

    # The Gatekeeper: Route users to Login if not authenticated
    if not st.session_state.is_authenticated:
        render_auth_page()
        return

    # User is authenticated, render the main app
    render_sidebar()
    render_header()

    if not st.session_state.messages:
        render_welcome_state()

    render_chat()

    queued_prompt = st.session_state.pending_prompt
    if queued_prompt:
        st.session_state.pending_prompt = None
        handle_query(queued_prompt)
        st.rerun()

    user_query = st.chat_input("Message BumbiroAI")

    if user_query:
        handle_query(user_query)
        st.rerun()


if __name__ == "__main__":
    main()