# scripts/auth_local.py
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def main():
    creds = None
    if os.path.exists("token.json"):
        print("token.json already exists in current folder.")
        return

    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print("Wrote token.json")

if __name__ == "__main__":
    main()
