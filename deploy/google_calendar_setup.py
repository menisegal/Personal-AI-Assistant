"""One-time Google Calendar OAuth setup.

Run this LOCALLY on a machine with a browser — never on the headless
Raspberry Pi. It opens a browser for you to log into Google and grant
calendar access, then saves the result to token.json (in the project root)
so the bot can use it afterwards without ever needing a browser itself.

Re-run this any time you need to re-authorize (e.g. token.json was deleted,
access was revoked, or you're granting a new scope).

Prerequisites (one-time, in Google Cloud Console):
1. Create/select a project at https://console.cloud.google.com/
2. Enable the "Google Calendar API" for it
3. Configure the OAuth consent screen (External user type is fine for
   personal use; add your own Google account as a test user)
4. Create credentials -> OAuth client ID -> Application type "Desktop app"
5. Download the JSON and save it as credentials.json in the project root
   (same folder as agent.py — NOT inside deploy/)

After running this script successfully, sync token.json to the Pi with:
    python deploy/deploy.py --service
"""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        print(f"[ERROR] {CREDENTIALS_PATH} not found.")
        print("Download an OAuth 2.0 'Desktop app' client secret from")
        print("https://console.cloud.google.com/apis/credentials and save it there.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    print(f"[DONE] Saved Google Calendar credentials to {TOKEN_PATH}")
    print("Now run: python deploy/deploy.py --service   (to sync it to the Pi)")


if __name__ == "__main__":
    main()
