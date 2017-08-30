#!/bin/python
import botocore
import boto3
import sys


def get_input(description, default_value):
    # Ask user for input or fall back to default value
    return raw_input('%s [%s]:' % (description, default_value)) \
        or default_value


def get_assumed_credentials(account_id, role_name):
    # Create an STS client object that represents a live connection to the
    # STS service.
    sts_client = boto3.client('sts')

    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name.
    assumedRoleObject = sts_client.assume_role(
        RoleArn='arn:aws:iam::%s:role/%s' % (account_id, role_name),
        RoleSessionName='session'
    )

    # From the response that contains the assumed role, get the temporary
    # credentials that can be used to make subsequent API calls.
    return assumedRoleObject['Credentials']


def get_ec2_client(credentials, region):
    # Create boto3 client by using assumed credentials from sts
    return boto3.client(
        'ec2',
        region_name=region,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
    )


def get_regions(client):
    response = client.describe_regions()
    return map(lambda region: region['RegionName'], response['Regions'])


def get_availibity_zones(client):
    response = client.describe_availability_zones(
        Filters=[
            {
                'Name': 'state',
                'Values': [
                    'available'
                ]
            }
        ]
    )
    return map(lambda az: az['ZoneName'], response['AvailabilityZones'])


def get_reserved_instances_offering_id(client, availability_zone):
    response = client.describe_reserved_instances_offerings(
        AvailabilityZone=availability_zone,
        IncludeMarketplace=False,
        MaxResults=1,
    )

    offerings = response['ReservedInstancesOfferings']

    if len(offerings) == 0:
        return None

    return offerings[0]['ReservedInstancesOfferingId']


def get_availability_zone_of_reserved_instance_offering(client, offering_id):
    response = client.describe_reserved_instances_offerings(
        ReservedInstancesOfferingIds=[
            offering_id
        ],
        MaxResults=1,
    )

    offerings = response['ReservedInstancesOfferings']

    if len(offerings) == 0:
        return None

    return offerings[0]['AvailabilityZone']


def main():
    role_name = get_input('Role name', 'Administrator')
    account_ids = get_input('Account IDs', '').split(',')

    if account_ids[0] == '':
        raise Exception('No account id specified')


    # Separate first account from the rest
    first_account_id, account_ids = account_ids[0], account_ids[1:]

    # Assume role in account
    credentials = get_assumed_credentials(first_account_id, role_name)

    # Get a list of all regions
    client = get_ec2_client(credentials, 'us-east-1')
    regions = get_regions(client)

    for region in regions:
        # Get AZs for specific region
        client = get_ec2_client(credentials, region)
        availability_zones = get_availibity_zones(client)

        for availability_zone in availability_zones:
            # Get offering ID for first account and find it in the other accounts
            offering_id = get_reserved_instances_offering_id(client, availability_zone)
            if offering_id:
                # Write output
                sys.stdout.write('\n' + offering_id + '\n')
                sys.stdout.write('-------------+-------------------\n')
                sys.stdout.write(first_account_id + ' | ' + availability_zone + '\n')

                for account_id in account_ids:
                    credentials = get_assumed_credentials(account_id, role_name)
                    client = get_ec2_client(credentials, region)
                    availability_zone = get_availability_zone_of_reserved_instance_offering(client, offering_id)

                    # Write output
                    sys.stdout.write(account_id + ' | ' + availability_zone + '\n')

                # Write output
                sys.stdout.write('-------------+-------------------\n')
                sys.stdout.flush()

if __name__ == '__main__':
    main()
