import requests
import time

def send_simple_ntfy_notification():
    """Sends a single, hardcoded notification to a specific ntfy.sh topic."""
    
    # --- IMPORTANT: Paste your ntfy.sh topic URL here ---
    topic_url = "https://ntfy.sh/nhag-vinted-alerts-2025"
    
    print(f"Attempting to send a test notification to: {topic_url}")
    
    try:
        response = requests.post(
            topic_url,
            data="This is a direct test from the Python script in GitHub Actions.",
            headers={"Title": "Vinted Scanner Test"},
            timeout=15
        )
        # Raise an exception if the status code is not successful (e.g., 404, 500)
        response.raise_for_status()
        
        print("---")
        print("SUCCESS: The request was sent without errors.")
        print(f"Status Code: {response.status_code}")
        print("Please check your ntfy.sh topic now.")
        print("---")

    except requests.exceptions.RequestException as e:
        print(f"---")
        print(f"❌ FAILED: The request could not be sent. Error: {e}")
        print("---")

# Run the test function
if __name__ == "__main__":
    send_simple_ntfy_notification()
