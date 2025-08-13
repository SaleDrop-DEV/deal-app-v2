import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

"""
function should be run once the url is inserted in google console.
"""
def watch_gmail_mailbox(user_email, credentials_json, pubsub_topic_name):
    """
    Sets up a watch on a user's Gmail mailbox to send notifications to a Pub/Sub topic.

    Args:
        user_email (str): The email address of the Gmail user to watch.
        credentials_json (dict): A dictionary containing the user's access_token, refresh_token,
                                 client_id, client_secret, and token_uri.
        pubsub_topic_name (str): The full Pub/Sub topic name (e.g., 'projects/your-project-id/topics/your-topic-name').
    Returns:
        dict: The response from the Gmail API watch request, or None on failure.
    """
    try:
        # Create Credentials object from dictionary
        credentials = Credentials.from_authorized_user_info(credentials_json)

        # Build the Gmail service
        service = build('gmail', 'v1', credentials=credentials)

        # Define the request body for the watch method
        request_body = {
            'topicName': pubsub_topic_name,
            'labelIds': ['INBOX'], # You can specify labels, e.g., ['INBOX', 'UNREAD']
        }

        # Call the watch method
        response = service.users().watch(userId=user_email, body=request_body).execute()
        print(f"Gmail watch setup successful for {user_email}: {response}")
        return response

    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        # Handle specific errors, e.g., invalid credentials, quota limits
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None

if __name__ == "__main__":
    # --- Define paths to credential files ---
    # This assumes utils.py is in the 'deals' app directory.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    COMMANDS_DIR = os.path.join(BASE_DIR, 'management', 'commands')
    CREDENTIALS_FILE = os.path.join(COMMANDS_DIR, 'credentials.json')
    TOKEN_FILE = os.path.join(COMMANDS_DIR, 'token.json')

    # --- Check if required files exist ---
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: Credentials file not found at {CREDENTIALS_FILE}")
        exit()
    if not os.path.exists(TOKEN_FILE):
        print(f"Error: Token file not found at {TOKEN_FILE}")
        print("Please run the 'fetch_emails' management command first to generate it.")
        exit()

    # --- Load and combine credentials ---
    # Load client config from credentials.json
    with open(CREDENTIALS_FILE, 'r') as f:
        client_config = json.load(f).get('installed', {})
        project_id = client_config.get('project_id')

    # Load user token from token.json
    with open(TOKEN_FILE, 'r') as f:
        token_config = json.load(f)

    # Combine into the required dictionary format
    credentials_info = {
        "token": token_config.get("token"),
        "refresh_token": token_config.get("refresh_token"),
        "token_uri": client_config.get("token_uri"),
        "client_id": client_config.get("client_id"),
        "client_secret": client_config.get("client_secret"),
        "scopes": token_config.get("scopes")
    }

    # --- Set your user and topic details here ---
    user_email = 'gijsgprojects@gmail.com'
    # IMPORTANT: Replace 'gmail-notifications' with the actual name of your Pub/Sub topic in GCP
    topic_name = 'gmail-notifications' 
    PUB_SUB_TOPIC = f"projects/{project_id}/topics/{topic_name}"

    print(f"Setting up watch for {user_email} on topic {PUB_SUB_TOPIC}")
    watch_gmail_mailbox(user_email, credentials_info, PUB_SUB_TOPIC)