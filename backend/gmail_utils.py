import base64
import datetime as dt
import os
import pickle
import webbrowser

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .celery_worker import audio_to_pdf

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


def download_attachments(service, messages, pdf_analyse=False, audio_analyse=False):
    """
    Download filtered attachments from messages, organized by member ID (from subject).
    PDFs and audio files are saved in separate subfolders inside each member folder.
    """
    # Decide which extensions to allow
    pdf_ext = [".pdf"] if pdf_analyse else []
    audio_ext = [".mp3", ".wav", ".m4a"] if audio_analyse else []

    all_files = []

    for msg_item in messages:
        msg = service.users().messages().get(userId="me", id=msg_item['id']).execute()

        # Extract subject → used as member folder name
        subject_header = next(
            (h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject'),
            "unknown"
        )
        member_id = subject_header.strip()

        # Base folder for this member
        member_folder = os.path.join("data", "attachments", member_id)

        # Create subfolders
        pdf_folder = os.path.join(member_folder, "pdf")
        audio_folder = os.path.join(member_folder, "audio")
        os.makedirs(pdf_folder, exist_ok=True)
        os.makedirs(audio_folder, exist_ok=True)

        parts = msg.get('payload', {}).get('parts', [])
        for part in parts:
            filename = part.get('filename')
            if not filename:
                continue

            # Determine type and folder
            ext = filename.lower().split('.')[-1]
            attachment_id = part['body'].get('attachmentId')
            if not attachment_id:
                continue

            if any(filename.lower().endswith(e) for e in pdf_ext):
                folder_path = pdf_folder
            elif any(filename.lower().endswith(e) for e in audio_ext):
                folder_path = audio_folder
            else:
                continue  # skip other files

            attachment = service.users().messages().attachments().get(
                userId="me", messageId=msg['id'], id=attachment_id
            ).execute()

            file_data = base64.urlsafe_b64decode(attachment['data'])
            attachment_path = os.path.join(folder_path, filename)
            all_files.append(filename)

            with open(attachment_path, "wb") as f:
                f.write(file_data)

            if folder_path == audio_folder:
                output_pdf_folder = os.path.join(member_folder, "pdf")
                os.makedirs(output_pdf_folder, exist_ok=True)
                audio_to_pdf.delay(attachment_path, output_pdf_folder,member_id)

            print(f"Saved: {attachment_path}")

    return all_files
