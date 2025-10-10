import os
import base64
import pickle
import datetime as dt
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import pickle
import webbrowser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import pickle
import webbrowser

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import webbrowser

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            try:
                # Try opening browser automatically
                creds = flow.run_local_server(port=8080, open_browser=True)
            except Exception:
                print("\n⚠️ Could not open browser. Please copy this URL and open manually:")
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(auth_url)
                print("\nThe local server will now wait for the OAuth redirect...")
                # Run server anyway, even if browser not opened
                creds = flow.run_local_server(port=8080, open_browser=False)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Build Gmail API service and return
    service = build("gmail", "v1", credentials=creds)
    return service


def search_emails(service, start_date, end_date):
    """Search for emails within a date range."""


    query = f"after:{start_date} before:{end_date} has:attachment"
    print(query)


    results = service.users().messages().list(userId="me", q=query).execute()
    print(results)
    messages = results.get("messages", [])
    return messages


def download_attachments(service, messages):
    """Download attachments from messages, organized by member ID (from subject)."""
    for msg_item in messages:
        msg = service.users().messages().get(userId="me", id=msg_item['id']).execute()
        subject_header = next(
            (h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject'),
            "unknown"
        )
        member_id = subject_header.strip()  # adjust parsing if needed

        folder_path = os.path.join("data", "audio", member_id)
        os.makedirs(folder_path, exist_ok=True)

        parts = msg.get('payload', {}).get('parts', [])
        for part in parts:
            if part.get('filename'):
                attachment_id = part['body'].get('attachmentId')
                if attachment_id:
                    attachment = service.users().messages().attachments().get(
                        userId="me", messageId=msg['id'], id=attachment_id
                    ).execute()
                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    attachment_path = os.path.join(folder_path, part['filename'])
                    with open(attachment_path, "wb") as f:
                        f.write(file_data)

