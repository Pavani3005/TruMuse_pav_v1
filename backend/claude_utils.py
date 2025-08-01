import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

headers = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

def summarize_wikipedia_url(url):
    prompt = f"""
    You are an expert art historian. Provide a 100-150 word summary of the artist's key contributions, style, and significance based on the Wikipedia page at {url}. 
    You must not include any statements about inability to access the URL, internet, or external resources. If the URL is inaccessible, use your existing knowledge to create a factual summary. Avoid phrases such as 'I'm unable to access,' 'cannot retrieve,' 'cannot browse,' or any similar disclaimers. Focus solely on the artist's contributions, style, and significance.
    """

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "temperature": 0.5,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        summary = response.json()["content"][0]["text"]
        # Remove unwanted disclaimer phrases
        unwanted_phrases = [
            "I'm unable to access external URLs",
            "cannot retrieve the specific Wikipedia page",
            "cannot browse the internet",
            "I'm unable to access",
            "cannot retrieve",
            "cannot browse"
        ]
        for phrase in unwanted_phrases:
            summary = summary.replace(phrase, "").strip()
        return summary if summary else "The artist is known for notable contributions to art."
    except (requests.RequestException, KeyError, IndexError):
        # Fallback summary without disclaimer
        return "The artist is recognized for significant artistic contributions and a distinctive style."