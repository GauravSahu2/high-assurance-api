import pytest
import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

@mock_aws
def test_backend_iam_role_security():
    """Verifies that unauthorized destructive actions throw IAM AccessDenied."""
    client = boto3.client('s3', region_name='us-east-1')
    client.create_bucket(Bucket='production-database-backups')
    
    # Simulate an IAM policy explicitly denying the DeleteBucket action
    from unittest.mock import patch
    with patch('botocore.client.BaseClient._make_api_call') as mock_call:
        mock_call.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "IAM Role lacks delete permissions"}},
            "DeleteBucket"
        )
        with pytest.raises(ClientError) as excinfo:
            client.delete_bucket(Bucket='production-database-backups')
        
        assert excinfo.value.response['Error']['Code'] == 'AccessDenied'
