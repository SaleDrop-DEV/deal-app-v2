from django.core.management.base import BaseCommand

import os
from groq import Groq, RateLimitError, APIConnectionError, AuthenticationError, GroqError
import json
import time

from business.models import SaleMessage, GroqAPIData

from deals.models import GmailToken, ScrapeData

API_KEY = GmailToken.objects.get(name="Groq").token_json['API_key']


def _create_fallback_response(reason: str, category: str = "error") -> dict:
    """Creates a standardized error response."""
    return {
        "is_safe": False,  # Default to unsafe on error
        "reason": reason,
        "category": category
    }

def moderate_message(
    message: str, 
    groq_api_key: str = None, 
    max_retries: int = 3, 
    initial_backoff: float = 1.0
) -> dict:
    """
    Moderates a user message to check for spam and inappropriate content with retries.
    
    Args:
        message: The user message to moderate.
        groq_api_key: Your Groq API key (or set GROQ_API_KEY environment variable).
        max_retries: The maximum number of times to retry the API call.
        initial_backoff: The initial wait time in seconds for the first retry.
    
    Returns:
        dict with keys:
            - is_safe (bool): True if message is okay, False if it should be blocked.
            - reason (str): Explanation of the decision.
            - category (str): Category of issue if unsafe.
    """
    
    # 1. Get API Key
    api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Groq API key must be provided or set in GROQ_API_KEY environment variable")
    
    # 2. Initialize Client
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        return _create_fallback_response(f"Client initialization error: {e}", "config_error")
        
    # 3. Define Prompt
    system_prompt = """
        You are a content moderation assistant. Brands can upload messages about sales and deals. I don't want any inappropriate content to be posted.

        Check for:
        - Weird/spammy content
        - Harassment or bullying
        - Hate speech or discrimination
        - Violence or threats
        - Sexual content
        - Scams or phishing attempts
        - Misinformation with harmful intent

        Respond ONLY with valid JSON in this exact format:
        {
            "is_safe": true/false,
            "reason": "brief explanation in dutch language",
            "category": "safe/spam/harassment/hate_speech/violence/sexual/scam/other"
        }
    """

    # 4. Retry Loop for API Call
    response_text_for_debugging = "" # Store last response text for error printing
    for attempt in range(max_retries):
        try:
            # Call Groq API
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Moderate this message: {message}"}
                ],
                model="llama-3.3-70b-versatile",  # Using a standard robust model
                temperature=1.0,
                max_tokens=150,
                response_format={"type": "json_object"}  # Enforce JSON output
            )
            
            # Check for empty response
            if not chat_completion.choices or not chat_completion.choices[0].message.content:
                print(f"WARNING: API returned an empty response (Attempt {attempt + 1})")
                raise GroqError("Empty response from API") # Trigger a retry

            response_text_for_debugging = chat_completion.choices[0].message.content
            
            # Parse the response (should be clean JSON)
            result = json.loads(response_text_for_debugging)
            
            # Validate the structure and types
            if not (
                isinstance(result.get("is_safe"), bool) and
                isinstance(result.get("reason"), str) and
                isinstance(result.get("category"), str)
            ):
                print(f"WARNING: API returned malformed JSON structure: {result} (Attempt {attempt + 1})")
                raise ValueError("Invalid response format from API") # Trigger a retry

            # Success!
            return result
        
        # 5. Handle Specific Errors
        except AuthenticationError as e:
            print(f"ERROR: Authentication error: {e}. Check your API key.")
            return _create_fallback_response("Invalid API key", "auth_error") # Non-recoverable
        
        except RateLimitError as e:
            print(f"WARNING: Rate limit hit (Attempt {attempt + 1}/{max_retries}): {e}")
            # Non-recoverable in this context
            return _create_fallback_response("Rate limit exceeded", "rate_limit")
        
        except (APIConnectionError, GroqError) as e:
            print(f"WARNING: Transient API error (Attempt {attempt + 1}/{max_retries}): {e}")
            # This is a good candidate for a retry

        except (json.JSONDecodeError, ValueError) as e:
            # ValueError is for our custom validation failure
            print(f"WARNING: Failed to parse/validate API response (Attempt {attempt + 1}/{max_retries}): {e}")
            print(f"DEBUG: Raw response was: {response_text_for_debugging}")
            # This is also a good candidate for a retry

        except Exception as e:
            print(f"ERROR: An unexpected error occurred (Attempt {attempt + 1}/{max_retries}): {e}")
            # Unknown error, might be transient
        
        # 6. Backoff Logic
        if attempt < max_retries - 1:
            sleep_time = initial_backoff * (2 ** attempt)
            print(f"INFO: Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
    # 7. Fallback after all retries fail
    print(f"ERROR: Failed to moderate message after {max_retries} attempts.")
    return _create_fallback_response("Moderation service failed after multiple retries", "api_failure")



class Command(BaseCommand):
    help = 'Moderate unreviewed sale messages using AI and flag for manual review if needed.'

    def handle(self, *args, **options):
        unreviewed_messages = SaleMessage.objects.filter(isReviewed=False)
        self.stdout.write(f"Found {unreviewed_messages.count()} unreviewed messages to moderate.")

        for message in unreviewed_messages:
            msg_to_moderate = f"Title: {message.title}\nGrabebr: {message.grabber}\nDescription: {message.description}"
            result = moderate_message(msg_to_moderate, groq_api_key=API_KEY)

            # Case 1: Moderation was successful and the content is safe.
            if result.get("is_safe") is True:
                message.isReviewed = True
                message.publicReady = True
                message.needsManualReview = False
                GroqAPIData.objects.create(
                    salemessage=message,
                    is_safe=result.get("is_safe"),
                    reason=result.get("reason"),
                    category=result.get("category")
                )
                self.stdout.write(self.style.SUCCESS(f"Message ID {message.id} approved automatically."))
            
            # Case 2: Moderation was successful and the content is NOT safe.
            elif result.get("is_safe") is False and "error" not in result.get("category", ""):
                message.isReviewed = True
                message.publicReady = False
                message.needsManualReview = True # Flag for a human to check.
                GroqAPIData.objects.create(
                    salemessage=message,
                    is_safe=result.get("is_safe"),
                    reason=result.get("reason"),
                    category=result.get("category")
                )
                self.stdout.write(self.style.WARNING(f"Message ID {message.id} flagged for manual review. Reason: {result.get('reason')}"))
            
            # Case 3: Moderation service failed (API error, timeout, etc.).
            else:
                ScrapeData.objects.create(
                    task="moderation_error",
                    succes = False,
                    major_error = False,
                    error = f"Moderation failed for Message ID {message.id}. Reason: {result.get('reason')}.",
                )
                message.isReviewed = False # Keep it as unreviewed to be picked up next time.
                message.needsManualReview = True # Flag for a human to check in case the service is down for a while.
                self.stderr.write(self.style.ERROR(f"Moderation failed for Message ID {message.id}. Reason: {result.get('reason')}. It will be retried later."))

            message.save()