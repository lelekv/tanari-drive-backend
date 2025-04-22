from flask import Flask, redirect, request, jsonify
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
import json

app = Flask(__name__)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Csak fejlesztéshez, HTTPS nélkül

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKENS_FILE = "tokens.json"

@app.route("/")
def index():
    return "Tanári Drive Backend fut rendesen! 🚀"

@app.route("/auth/start")
def auth_start():
    print("Redirect URI:", REDIRECT_URI)
    print("Client ID:", CLIENT_ID)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    auth_url, _ = flow.authorization_url(prompt="consent", include_granted_scopes="true")
    return redirect(auth_url)

@app.route("/auth/callback")
def auth_callback():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    email = creds.id_token.get("email")

    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            tokens = json.load(f)
    else:
        tokens = {}

    tokens[email] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    return f"Sikeres hitelesítés: {email}"

@app.route("/upload-file", methods=["POST"])
def upload_file():
    data = request.json
    email = data.get("email")
    filename = data.get("filename")
    content = data.get("content")

    if not all([email, filename, content]):
        return {"error": "Hiányzó mezők"}, 400

    if not os.path.exists(TOKENS_FILE):
        return {"error": "Nincs tokenfájl"}, 403

    with open(TOKENS_FILE, "r") as f:
        tokens = json.load(f)

    if email not in tokens:
        return {"error": "Nincs token ehhez a felhasználóhoz"}, 403

    creds = Credentials(**tokens[email])
    drive = build("drive", "v3", credentials=creds)

    file_metadata = {"name": filename}
    media = {"mimeType": "text/plain", "body": content}

    file = drive.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return {"message": "Sikeres feltöltés", "file_id": file.get("id")}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
