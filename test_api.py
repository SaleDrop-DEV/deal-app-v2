import requests
import json

def test_django_api_authentication(base_url, username, password):
    """
    Tests the JWT authentication flow for your Django REST Framework API.

    Args:
        base_url (str): The base URL of your Django API (e.g., "http://127.0.0.1:8000/api/").
        username (str): The username (or email, if configured) for authentication.
        password (str): The password for authentication.
    """
    print(f"Attempting to authenticate user: {username}")

    # 1. Obtain JWT Token
    token_url = f"{base_url}token/"
    login_data = {
        "username": username, # Use 'email' if ACCOUNT_AUTHENTICATION_METHOD is 'email'
                           # Otherwise, use 'username': username
        "password": password
    }
    headers = {"Content-Type": "application/json"}

    try:
        print(f"Requesting token from: {token_url}")
        response = requests.post(token_url, data=json.dumps(login_data), headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        token_data = response.json()
        access_token = token_data.get("access")
        refresh_token = token_data.get("refresh")

        if access_token:
            print("Successfully obtained JWT tokens:")
            print(f"  Access Token: {access_token[:30]}...") # Print first 30 chars
            print(f"  Refresh Token: {refresh_token[:30]}...") # Print first 30 chars
        else:
            print("Failed to obtain access token. Response:")
            print(json.dumps(token_data, indent=2))
            return

    except requests.exceptions.RequestException as e:
        print(f"Error during token acquisition: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server response: {e.response.text}")
        return
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response for token: {response.text}")
        return

    # 2. Use Access Token to access a protected endpoint
    protected_url = f"{base_url}stores/" # Example protected endpoint
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\nAttempting to access protected endpoint: {protected_url}")
        print(f"  With Authorization Header: Bearer {access_token[:30]}...")
        response = requests.get(protected_url, headers=auth_headers)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        protected_data = response.json()

        print("\nSuccessfully accessed protected endpoint!")
        print("Response data (first 500 chars):")
        print(json.dumps(protected_data, indent=2)[:500])
        if len(json.dumps(protected_data, indent=2)) > 500:
            print("...")

    except requests.exceptions.RequestException as e:
        print(f"\nError accessing protected endpoint: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server response: {e.response.text}")
        print("Authentication might have failed or token is invalid/expired.")
        return
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response from protected endpoint: {response.text}")
        return

# --- How to run this function ---
if __name__ == "__main__":
    # IMPORTANT: Replace with your actual Django backend URL and user credentials
    DJANGO_BASE_API_URL = "http://127.0.0.1:8000/api/"
    TEST_USERNAME = "gijsgroenendijk@yahoo.com" # Or 'your_username' if not using email auth
    TEST_PASSWORD = "PatronHein1913"

    test_django_api_authentication(DJANGO_BASE_API_URL, TEST_USERNAME, TEST_PASSWORD)