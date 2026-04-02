import boto3
from moto import mock_aws


def remediate_drift(ec2_client, group_id: str, expected_ports: set):
    response = ec2_client.describe_security_groups(GroupIds=[group_id])
    for rule in response["SecurityGroups"][0].get("IpPermissions", []):
        from_port = rule.get("FromPort")
        if from_port not in expected_ports:
            ec2_client.revoke_security_group_ingress(
                GroupId=group_id, IpPermissions=[rule]
            )


@mock_aws
def test_infrastructure_drift_remediation():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg = ec2.create_security_group(
        GroupName="prod-sg", Description="Prod", VpcId=vpc["Vpc"]["VpcId"]
    )

    ec2.authorize_security_group_ingress(
        GroupId=sg["GroupId"],
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    )

    expected_ports = {80, 443}

    remediate_drift(ec2, sg["GroupId"], expected_ports)

    response = ec2.describe_security_groups(GroupIds=[sg["GroupId"]])
    actual_ports = {
        rule["FromPort"]
        for rule in response["SecurityGroups"][0].get("IpPermissions", [])
    }

    drift = actual_ports - expected_ports
    assert (
        drift == set()
    ), f"Drift Remediation failed! Unauthorized ports remain: {drift}"
