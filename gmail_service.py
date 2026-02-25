import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailService:
    def __init__(self, credentials=None):
        self.creds = credentials
        if not self.creds or not self.creds.valid:
             raise ValueError("Valid credentials must be provided or authentication flow must be run.")

        self.service = build('gmail', 'v1', credentials=self.creds)

    @staticmethod
    def authenticate_user(credentials_path='credentials.json', force_new=False):
        """
        Authenticates a user and returns their credentials.
        """
        creds = None
        
        # Only check token.json if we are NOT forcing a new login
        if not force_new and os.path.exists('token.json'):
             try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
             except:
                pass 
        
        if not creds or not creds.valid:
            if not force_new and creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    creds = None
            
            if not creds:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                # Ensure we force account picker if forcing new login
                # prompt='select_account' forces the account picker
                kwargs = {'port': 0}
                if force_new:
                    # We can't easily pass 'prompt' to run_local_server directly in all versions, 
                    # but we can set it on the flow authorization url if needed.
                    # Standard run_local_server usually just opens the auth URL.
                    # flow.authorization_url(prompt='select_account')
                    # Actually, run_local_server handles the whole flow. 
                    # Let's try to just run it; usually it cookies auth unless we explicitly ask otherwise.
                    # To force account picker, we might need to modify the flow or just rely on user switching in browser.
                     pass

                creds = flow.run_local_server(port=0)
        
        return creds

    @staticmethod
    def get_service_email(creds):
        try:
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except:
            return None

    def get_unread_messages(self, max_results=20):
        """Lists unread messages in the user's mailbox."""
        try:
            results = self.service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def get_message_content(self, msg_id):
        """Gets the content of a message."""
        try:
            message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = message['payload']
            headers = payload.get('headers', [])
            
            subject = ""
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                    break
            
            body = ""
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
            return ""

    def move_to_spam(self, msg_id):
        """Moves a message to the SPAM category and removes it from INBOX."""
        try:
            # First, check if SPAM label exists (standard Gmail behavior)
            # Actually, we can just use the 'trash' method or move to 'SPAM' label
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={
                    'removeLabelIds': ['INBOX', 'UNREAD'],
                    'addLabelIds': ['SPAM']
                }
            ).execute()
            print(f"Message {msg_id} moved to SPAM.")
        except HttpError as error:
            print(f'An error occurred: {error}')

    def trash_message(self, msg_id):
        """Trashes a message."""
        try:
            self.service.users().messages().trash(userId='me', id=msg_id).execute()
            print(f"Message {msg_id} trashed.")
        except HttpError as error:
            print(f'An error occurred: {error}')

    def get_email_address(self):
        """Gets the email address of the authenticated user."""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

if __name__ == "__main__":
    # This won't run without credentials.json
    try:
        creds = GmailService.authenticate_user()
        service = GmailService(creds)
        print("Gmail service initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gmail service: {e}")
