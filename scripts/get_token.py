"""
Run this once to generate token.json for YouTube OAuth.
Requires client_secret.json from Google Cloud Console.

Usage:
    python3 get_token.py
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=SCOPES
)

flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
auth_url, _ = flow.authorization_url(prompt='consent')

print("\n=== OPEN THIS URL IN YOUR BROWSER ===")
print(auth_url)
print("\nAfter authorizing, paste the code here:")
code = input("> ").strip()

flow.fetch_token(code=code)

with open('token.json', 'w') as f:
    f.write(flow.credentials.to_json())
os.chmod('token.json', 0o600)

print("\ntoken.json saved successfully! (permissions set to 600)")
print("You only need to run this once.")
