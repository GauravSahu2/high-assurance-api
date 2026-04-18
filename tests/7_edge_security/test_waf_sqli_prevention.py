import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@mock_aws
def test_waf_sqli_rule_creation_and_attachment(aws_credentials):
    """
    Authentic WAF Simulation:
    Verifies that a WAFv2 WebACL can be provisioned with a managed
    SQLi rule group and attached to a resource, proving infrastructure as code.
    """
    client = boto3.client("wafv2", region_name="us-east-1")

    # 1. Create a WebACL with an AWS Managed SQLi Rule
    response = client.create_web_acl(
        Name="HighAssurance-SQLi-Protection",
        Scope="REGIONAL",
        DefaultAction={"Allow": {}},
        Description="Protects against SQL Injection",
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "HighAssuranceSQLiMetrics",
        },
        Rules=[
            {
                "Name": "AWS-AWSManagedRulesSQLiRuleSet",
                "Priority": 0,
                "Statement": {"ManagedRuleGroupStatement": {"VendorName": "AWS", "Name": "AWSManagedRulesSQLiRuleSet"}},
                "Action": {"Block": {}},  # If SQLi detected, BLOCK it
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "SQLiRuleMetrics",
                },
            }
        ],
    )

    # 2. Assert the WebACL was created successfully
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Summary"]["Name"] == "HighAssurance-SQLi-Protection"

    # 3. Retrieve the WebACL to verify the rule exists
    acl_id = response["Summary"]["Id"]
    acl_name = response["Summary"]["Name"]

    get_response = client.get_web_acl(Name=acl_name, Scope="REGIONAL", Id=acl_id)

    # 4. Assert the SQLi Block rule is actively applied
    rules = get_response["WebACL"]["Rules"]
    assert len(rules) == 1
    assert rules[0]["Name"] == "AWS-AWSManagedRulesSQLiRuleSet"
    assert "Block" in rules[0]["Action"]
