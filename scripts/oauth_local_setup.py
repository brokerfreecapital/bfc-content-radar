import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
]

def main():
    """
    One-time script.
    Opens browser, asks for consent, prints refresh token.
    """

    CLIENT_SECRETS_FILE = "client_secret.json"

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
    )

    creds = flow.run_local_server(
        port=8090,
        access_type="offline",
        prompt="consent",
    )

    with open(CLIENT_SECRETS_FILE, "r") as f:
        raw = json.load(f)

    client_id = raw["installed"]["client_id"]
    client_secret = raw["installed"]["client_secret"]

    print("\n================ COPY THESE =================\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("\n============================================\n")

if __name__ == "__main__":
    main()
