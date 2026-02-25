import os
import base64
import json
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def _get_client_config():
    """Load OAuth client config from Streamlit Secrets or fallback to credentials.json."""
    if "google_oauth" in st.secrets:
        secret = st.secrets["google_oauth"]
        return {
            "web": {
                "client_id": secret["client_id"],
                "client_secret": secret["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [secret["redirect_uri"]],
            }
        }
    # Local dev fallback
    creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
    if os.path.exists(creds_path):
        with open(creds_path) as f:
            data = json.load(f)
        # Wrap "installed" type as "web" so Flow works the same way
        key = "web" if "web" in data else "installed"
        cfg = data[key]
        return {
            "web": {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "auth_uri": cfg.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": cfg.get("token_uri", "https://oauth2.googleapis.com/token"),
                "redirect_uris": cfg.get("redirect_uris", ["http://localhost"]),
            }
        }
    raise FileNotFoundError(
        "No OAuth credentials found. Add [google_oauth] to Streamlit Secrets "
        "or place credentials.json in the project folder."
    )

def _get_redirect_uri():
    """Return the redirect URI — the app URL on cloud, localhost for local dev."""
    if "google_oauth" in st.secrets:
        return st.secrets["google_oauth"]["redirect_uri"]
    redirect_uri = "http://localhost"
    # st.write(f"DEBUG: Using redirect_uri: {redirect_uri}") # Uncomment if debugging locally
    return redirect_uri


class GmailService:
    def __init__(self, credentials=None):
        self.creds = credentials
        if not self.creds or not self.creds.valid:
            raise ValueError("Valid credentials must be provided.")
        self.service = build('gmail', 'v1', credentials=self.creds)

    @staticmethod
    def get_auth_url():
        """Return the Google OAuth URL the user must visit."""
        client_config = _get_client_config()
        redirect_uri = _get_redirect_uri()
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account',
        )
        st.session_state['oauth_client_config'] = client_config
        return auth_url

    @staticmethod
    def exchange_code(code: str):
        """Exchange the auth code (from query params) for credentials."""
        client_config = st.session_state.get('oauth_client_config') or _get_client_config()
        redirect_uri = _get_redirect_uri()
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
        flow.fetch_token(code=code)
        return flow.credentials

    @staticmethod
    def get_service_email(creds):
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except Exception as e:
            st.error(f"Failed to retrieve user profile: {e}")
            return None

    def get_unread_messages(self, max_results=20):
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:unread', maxResults=max_results
            ).execute()
            return results.get('messages', [])
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def get_message_content(self, msg_id):
        try:
            message = self.service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            payload = message['payload']
            headers = payload.get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            body = ''
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            else:
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            return f"Subject: {subject}\n{body}"
        except HttpError as error:
            print(f'An error occurred: {error}')
            return ''

    def move_to_spam(self, msg_id):
        try:
            self.service.users().messages().modify(
                userId='me', id=msg_id,
                body={'removeLabelIds': ['INBOX', 'UNREAD'], 'addLabelIds': ['SPAM']}
            ).execute()
        except HttpError as error:
            print(f'An error occurred: {error}')

    def trash_message(self, msg_id):
        try:
            self.service.users().messages().trash(userId='me', id=msg_id).execute()
        except HttpError as error:
            print(f'An error occurred: {error}')

    def get_email_address(self):
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
