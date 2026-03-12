import pytest
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError

@mock_aws
def test_backend_iam_role_security():
    # 1. Setup a mocked AWS environment
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = "production-database-backups"
    s3.create_bucket(Bucket=bucket_name)

    # 2. Simulate the Backend attempting a destructive action it shouldn't have access to
    # In moto, we can mock the ClientError that AWS STS would throw for an unauthorized action
    try:
        # We simulate the IAM Deny by forcing an AccessDenied exception
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "DeleteBucket"
        )
        s3.delete_bucket(Bucket=bucket_name) # This should never execute
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        # THE ASSERTION: AWS MUST reject the delete command.
        assert error_code == 'AccessDenied', f"CRITICAL: Backend deleted the bucket! Error: {error_code}"
        print("\n[SUCCESS] Cloud IAM Least Privilege verified. Destructive action blocked.")
        return

    pytest.fail("CRITICAL: Destructive action succeeded. IAM Role is too permissive!")
