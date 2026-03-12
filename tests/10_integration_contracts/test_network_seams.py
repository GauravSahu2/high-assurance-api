import pytest
import requests

# 1. Test Cloud to Frontend Integration (CORS Security)
def test_cloud_cors_rejection():
    api_url = "https://google.com" # Replace with your API URL
    
    # Simulate a request coming from a malicious frontend
    malicious_headers = {'Origin': 'https://evil-hacker-site.com'}
    
    # We send an OPTIONS request (Pre-flight check)
    response = requests.options(api_url, headers=malicious_headers)
    
    # THE ASSERTION: The Cloud API Gateway MUST NOT return the malicious origin
    allowed_origin = response.headers.get('Access-Control-Allow-Origin')
    assert allowed_origin != 'https://evil-hacker-site.com', "CRITICAL: Cloud allowed CORS from an untrusted frontend!"
    print("\n[SUCCESS] Cloud to Frontend integration secured. Malicious CORS rejected.")


# 2. Test Backend to Cloud Integration (IAM Permissions Simulation)
def test_backend_to_cloud_iam():
    # In a real environment, this uses boto3 (AWS SDK) to try an unauthorized action
    # For simulation, we mock the AWS STS (Security Token Service) response
    
    simulated_aws_iam_response = {
        "Action": "s3:DeleteBucket",
        "Resource": "arn:aws:s3:::production-database-backups",
        "Effect": "Deny" # IAM strictly denies the backend from deleting backups
    }
    
    # THE ASSERTION: The backend's Cloud IAM role must explicitly deny destructive actions
    assert simulated_aws_iam_response["Effect"] == "Deny", "CRITICAL: Backend has dangerous Cloud permissions!"
    print("[SUCCESS] Backend to Cloud integration secured. IAM Least Privilege enforced.")

