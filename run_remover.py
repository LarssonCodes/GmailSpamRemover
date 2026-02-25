from gmail_service import GmailService
from spam_filter import SpamFilter
import time

def main():
    print("Initializing Gmail Spam Remover...")
    
    # Get user email
    target_email = input("Enter your Gmail address: ").strip()
    
    # Define token path for this user
    user_token_path = f'token_{target_email}.json'
    
    # Check for migration: if generic token.json exists, see who it belongs to
    import os
    if os.path.exists('token.json'):
        print("Checking existing login session...")
        try:
            temp_service = GmailService(token_path='token.json')
            existing_email = temp_service.get_email_address()
            if existing_email:
                new_path = f'token_{existing_email}.json'
                if not os.path.exists(new_path):
                    print(f"Migrating session for {existing_email}...")
                    os.rename('token.json', new_path)
                else:
                    # New path exists, generic one is redundant or old
                    pass
        except Exception as e:
            print(f"Warning during migration: {e}")

    try:
        # Initialize components
        spam_filter = SpamFilter()
        print("Spam filter loaded successfully.")
        
        # Initialize with specific token path
        gmail = GmailService(token_path=user_token_path)
        authenticated_email = gmail.get_email_address()
        
        if authenticated_email and authenticated_email.lower() != target_email.lower():
            print(f"\nAuthenticated as '{authenticated_email}' but you entered '{target_email}'.")
            print(f"The token file '{user_token_path}' seems to belong to a different account.")
            print("Cleaning up invalid token...")
            
            if os.path.exists(user_token_path):
                os.remove(user_token_path)
            
            # Re-initialize to trigger auth flow for the correct targeted email
            print("Please authenticate with the correct account in the browser...")
            gmail = GmailService(token_path=user_token_path)
            authenticated_email = gmail.get_email_address()
            
            print(f"Successfully authenticated as {authenticated_email}")
        else:
            print(f"Successfully authenticated as {authenticated_email}")

        print("\nScanning for unread emails...")
        messages = gmail.get_unread_messages(max_results=50)
        
        if not messages:
            print("No unread messages found.")
            return

        print(f"Found {len(messages)} unread messages. Analyzing...")
        
        spam_count = 0
        ham_count = 0
        
        spam_ids = []
        
        for msg in messages:
            msg_id = msg['id']
            content = gmail.get_message_content(msg_id)
            
            if not content:
                continue
                
            # Extract subject for logging (optional, get_message_content returns Subject: ...)
            lines = content.split('\n')
            subject = lines[0] if lines else "No Subject"
            
            if spam_filter.is_spam(content):
                print(f"[SPAM] {subject}")
                # Store ID for later processing
                spam_ids.append(msg_id)
                spam_count += 1
            else:
                print(f"[HAM]  {subject}")
                ham_count += 1
                
        print(f"\nAnalysis complete.")
        print(f"Processed: {len(messages)}")
        print(f"Spam detected: {spam_count}")
        print(f"Ham detected: {ham_count}")
        
        if spam_count > 0:
            confirm = input(f"\nDo you want to move these {spam_count} spam emails to the SPAM folder? (y/n): ")
            if confirm.lower() == 'y':
                print("Moving messages to Spam folder...")
                for spam_id in spam_ids:
                    gmail.move_to_spam(spam_id)
                print("Done.")
            else:
                print("Operation cancelled.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure 'credentials.json' is in the current directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
