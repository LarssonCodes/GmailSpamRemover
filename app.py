import streamlit as st
import pandas as pd
from gmail_service import GmailService
from spam_filter import SpamFilter
import os
import time

# Page Configuration
st.set_page_config(
    page_title="Gmail Spam Remover",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for aesthetics
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main-header {
        font-size: 2.5rem;
        color: #4B4B4B;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #6C757D;
    }
    .stButton>button {
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: 600;
    }
    .spam-tag {
        background-color: #FFCDD2;
        color: #C62828;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .ham-tag {
        background-color: #C8E6C9;
        color: #2E7D32;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'gmail_service' not in st.session_state:
    st.session_state.gmail_service = None
if 'spam_filter' not in st.session_state:
    st.session_state.spam_filter = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'auth_url' not in st.session_state:
    st.session_state.auth_url = None

# ── Auto-handle Google's redirect (code arrives as a query param) ──────────
_params = st.query_params
if "code" in _params and not st.session_state.authenticated:
    _code = _params["code"]
    try:
        with st.spinner("Completing sign-in…"):
            _creds = GmailService.exchange_code(_code)
            _email = GmailService.get_service_email(_creds)
            if _email:
                st.session_state.gmail_service = GmailService(_creds)
                st.session_state.user_email = _email
                st.session_state.authenticated = True
                st.session_state.auth_url = None
                st.query_params.clear()   # remove ?code=... from URL
                st.rerun()
    except Exception as _e:
        st.error(f"Auto sign-in failed: {_e}")
        st.query_params.clear()

def init_services():
    try:
        if st.session_state.spam_filter is None:
            with st.spinner('Loading Spam Filter Model...'):
                st.session_state.spam_filter = SpamFilter()
    except Exception as e:
        st.error(f"Error initializing services: {e}")

def start_login():
    """Step 1 — redirect user to Google's auth page."""
    try:
        auth_url = GmailService.get_auth_url()
        # Open Google's sign-in page in the same tab
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
        st.session_state.auth_url = auth_url
    except Exception as e:
        st.error(f"Could not generate login URL: {e}")

def finish_login(code: str):
    """Fallback: manually exchange a pasted code."""
    try:
        with st.spinner('Verifying...'):
            creds = GmailService.exchange_code(code.strip())
            email = GmailService.get_service_email(creds)
            if email:
                st.session_state.gmail_service = GmailService(creds)
                st.session_state.user_email = email
                st.session_state.authenticated = True
                st.session_state.auth_url = None
                st.rerun()
            else:
                st.error("Authenticated but could not retrieve email address.")
    except Exception as e:
        st.error(f"Authentication failed: {e}")

def scan_emails():
    if not st.session_state.gmail_service:
        st.warning("Please login first.")
        return

    with st.spinner('Scanning unread emails...'):
        gmail = st.session_state.gmail_service
        filter_model = st.session_state.spam_filter
        
        raw_messages = gmail.get_unread_messages(max_results=50)
        
        processed_messages = []
        if raw_messages:
            progress_bar = st.progress(0)
            for i, msg in enumerate(raw_messages):
                msg_id = msg['id']
                content = gmail.get_message_content(msg_id)
                
                if content:
                    lines = content.split('\n')
                    # Subject usually comes from the first line in our helper
                    subject = lines[0].replace("Subject: ", "") if lines else "No Subject"
                    # Body is the rest
                    body = "\n".join(lines[1:])[:200] + "..." # Snippet
                    
                    is_spam = filter_model.is_spam(content)
                    
                    processed_messages.append({
                        'id': msg_id,
                        'Subject': subject,
                        'Snippet': body,
                        'Prediction': 'SPAM' if is_spam else 'HAM',
                        'Select': False 
                    })
                
                progress_bar.progress((i + 1) / len(raw_messages))
            
            st.session_state.messages = processed_messages
            st.success(f"Scanned {len(processed_messages)} emails.")
        else:
            st.info("No unread messages found.")
            st.session_state.messages = []

def move_spam():
    if not st.session_state.messages:
        return
        
    spam_msgs = [msg for msg in st.session_state.messages if msg['Prediction'] == 'SPAM']
    if not spam_msgs:
        st.info("No spam detected to move.")
        return
        
    count = 0
    with st.spinner(f"Moving {len(spam_msgs)} spam emails to Spam folder..."):
        for msg in spam_msgs:
            st.session_state.gmail_service.move_to_spam(msg['id'])
            count += 1
    
    st.success(f"Moved {count} emails to Spam.")
    # Clear local list or re-scan
    st.session_state.messages = [] # Clear for now
    time.sleep(2)
    st.rerun()

# --- UI Structure ---

# Sidebar
with st.sidebar:
    st.title("Settings")
    
    if st.session_state.authenticated:
        st.success(f"Logged in as: {st.session_state.user_email}")
        
        if st.button("Switch Account"):
            st.session_state.authenticated = False
            st.session_state.gmail_service = None
            st.session_state.user_email = ""
            start_login()

        if st.button("Logout"):
            st.session_state.gmail_service = None
            st.session_state.authenticated = False
            st.session_state.user_email = ""
            st.session_state.auth_url = None
            st.rerun()
    elif st.session_state.auth_url:
        # Step 2 — waiting for user to paste the code
        st.markdown(f"[**Click here to authorize with Google**]({st.session_state.auth_url})")
        st.caption("After authorizing, Google will show a code. Paste it below:")
        code_input = st.text_input("Paste authorization code here", key="oauth_code")
        if st.button("Submit Code"):
            if code_input:
                finish_login(code_input)
            else:
                st.warning("Please paste the code from Google first.")
        if st.button("Cancel"):
            st.session_state.auth_url = None
            st.rerun()
    else:
        st.info("Not logged in")
        if st.button("Login with Google"):
            start_login()

    st.markdown("---")
    st.write("Current Model: Naive Bayes")

    # Initialize services on load (mainly spam filter)
    init_services()

    # Model accuracy
    if st.session_state.spam_filter:
        with st.spinner("Computing accuracy..."):
            acc = st.session_state.spam_filter.get_accuracy(data_dir=os.path.dirname(__file__))
        if acc is not None:
            st.metric("Model Accuracy", f"{acc}%")
        else:
            st.warning("Could not compute accuracy.")


# Main Content
st.markdown('<div class="main-header">Intelligent Gmail <span style="color:#D93025">Spam Remover</span></div>', unsafe_allow_html=True)
st.markdown("Automate your inbox cleanup with Machine Learning.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", "Connected" if st.session_state.authenticated else "Disconnected")
with col2:
    st.metric("Emails Scanned", len(st.session_state.messages) if st.session_state.messages else 0)
with col3:
    spam_count = len([m for m in st.session_state.messages if m['Prediction'] == 'SPAM']) if st.session_state.messages else 0
    st.metric("Spam Detected", spam_count, delta_color="inverse")

st.markdown("---")

if st.session_state.authenticated:
    col_scan, col_action = st.columns([1, 4])
    with col_scan:
        if st.button("🔍 Scan Inbox", use_container_width=True):
            scan_emails()
    
    if st.session_state.messages:
        # Display Data
        
        # Determine row styling? Streamlit dataframe doesn't support row styling easily yet without pandas styler
        # We'll just show a clean table
        
        df = pd.DataFrame(st.session_state.messages)
        
        # Add a selection mechanism? 
        # For simplicity in this v1, we'll just have bulk actions based on prediction
        # or we can use st.data_editor if new streamlit
        
        st.subheader("Scan Results")
        
        edited_df = st.data_editor(
            df[['Subject', 'Snippet', 'Prediction', 'Select']],
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select to perform actions",
                    default=False,
                ),
                "Snippet": st.column_config.TextColumn(
                    "Content Snippet",
                    width="large"
                ),
                "Prediction": st.column_config.TextColumn(
                    "Type",
                    width="small"
                )
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        # Action Buttons
        st.markdown("### Actions")
        c1, c2, c3 = st.columns(3)
        
        # Helper to get selected attributes
        # We need the real IDs. Since we didn't sort, we can use the index from the edited_df
        # providing the user didn't shuffle things (Streamlit data editor doesn't sort by default unless configured)
        # To be safe, let's look up by Subject/Snippet or just trust index for now in this v1.
        
        # Improved: let's re-map selection to IDs based on index, assuming direct mapping
        selected_rows = edited_df[edited_df['Select']]
        selected_indices = selected_rows.index.tolist()
        
        selected_ids = [st.session_state.messages[i]['id'] for i in selected_indices if i < len(st.session_state.messages)]

        with c1:
            if st.button("Move ALL Detected Spam to Spam Folder"):
                move_spam()
        
        with c2:
            if st.button("Move SELECTED to Spam"):
                if not selected_ids:
                    st.warning("No emails selected.")
                else:
                    count = 0
                    with st.spinner(f"Moving {len(selected_ids)} selected emails to Spam..."):
                        for msg_id in selected_ids:
                            st.session_state.gmail_service.move_to_spam(msg_id)
                            count += 1
                    st.success(f"Moved {count} emails to Spam.")
                    st.session_state.messages = [] # Force rescan
                    time.sleep(1)
                    st.rerun()

        with c3:
            if st.button("Trash SELECTED"):
                if not selected_ids:
                    st.warning("No emails selected.")
                else:
                    count = 0
                    with st.spinner(f"Trashing {len(selected_ids)} selected emails..."):
                        for msg_id in selected_ids:
                            st.session_state.gmail_service.trash_message(msg_id)
                            count += 1
                    st.success(f"Trashed {count} emails.")
                    st.session_state.messages = [] # Force rescan
                    time.sleep(1)
                    st.rerun()
        
else:
    st.info("👈 Please log in using the sidebar to start.")

