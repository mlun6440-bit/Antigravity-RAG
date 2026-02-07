#!/usr/bin/env python3
"""
Simple script to trigger Google Sheets OAuth authentication.
This will open a browser window for you to authorize the app.
"""

import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def authenticate():
    """Trigger OAuth flow to get fresh credentials."""
    creds = None

    # Check if token.json exists
    if os.path.exists('token.json'):
        print("Found existing token.json, loading...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            try:
                creds.refresh(Request())
                print("✓ Token refreshed successfully!")
            except Exception as e:
                print(f"✗ Refresh failed: {e}")
                print("Need to re-authenticate...")
                creds = None

        if not creds:
            if not os.path.exists('credentials.json'):
                print("✗ ERROR: credentials.json not found!")
                print("Please download OAuth credentials from Google Cloud Console")
                sys.exit(1)

            print("\n" + "="*60)
            print("GOOGLE SHEETS AUTHENTICATION")
            print("="*60)
            print("\nA browser window will open shortly.")
            print("Please:")
            print("1. Select your Google account")
            print("2. Click 'Allow' to grant spreadsheet access")
            print("3. Return to this terminal after authorization")
            print("\nWaiting for authorization...")
            print("="*60 + "\n")

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("\n✓ Authentication successful!")
        print("✓ token.json saved for future use")
    else:
        print("✓ Valid credentials already exist!")

    return creds

if __name__ == '__main__':
    print("Starting Google Sheets authentication...\n")
    creds = authenticate()
    if creds and creds.valid:
        print("\n" + "="*60)
        print("SUCCESS - You're authenticated!")
        print("="*60)
        print("\nYou can now start the web server:")
        print("  py web_app.py")
        print("\nOr use the asset updater:")
        print("  py tools/asset_updater.py update <asset_id> <field> <value>")
    else:
        print("\n✗ Authentication failed")
        sys.exit(1)
