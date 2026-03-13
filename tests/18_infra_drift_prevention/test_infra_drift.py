from moto import mock_aws
import boto3

@mock_aws
def test_infrastructure_drift():
    """Detects if unauthorized ports are opened on Cloud Infrastructure."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    sg = ec2.create_security_group(GroupName='prod-sg', Description='Prod', VpcId=vpc['Vpc']['VpcId'])

    # SIMULATE DRIFT: Someone manually opens SSH port 22 in production
    ec2.authorize_security_group_ingress(
        GroupId=sg['GroupId'],
        IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}]
    )

    # MONITOR LOGIC: Read actual state from cloud
    response = ec2.describe_security_groups(GroupIds=[sg['GroupId']])
    actual_ports = {rule['FromPort'] for rule in response['SecurityGroups'][0]['IpPermissions']}
    
    expected_ports = {80, 443} # We only expect Web traffic
    
    drift = actual_ports - expected_ports
    assert 22 in drift, "Drift Monitor failed to detect the unauthorized SSH port!"
