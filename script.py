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


def get_ec2_client_by_assumed_role(account_id, role_name, region):
    # Get credentials
    credentials = get_assumed_credentials(account_id, role_name)

    # Create boto3 client by using assumed credentials from sts
    return boto3.client(
        'ec2',
        region_name=region,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
    )


def get_ec2_client_by_profile_name(profile_name, region):
    # Create boto3 client by using a profile name
    return boto3.Session(profile_name=profile_name).client('ec2', region_name=region)


def get_regions(client):
    response = client.describe_regions()
    return map(lambda region: region['RegionName'], response['Regions'])


def get_availabity_zones(client):
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
    try:
        response = client.describe_reserved_instances_offerings(
            AvailabilityZone=availability_zone,
            IncludeMarketplace=False,
            MaxResults=1,
        )

        offerings = response['ReservedInstancesOfferings']

        if len(offerings) == 0:
            return ''

        return offerings[0]['ReservedInstancesOfferingId']
    except:
        return ''


def get_availability_zone_of_reserved_instance_offering(client, offering_id):
    try:
        response = client.describe_reserved_instances_offerings(
            ReservedInstancesOfferingIds=[
                offering_id
            ],
            MaxResults=1,
        )

        offerings = response['ReservedInstancesOfferings']

        if len(offerings) == 0:
            return ''

        return offerings[0]['AvailabilityZone']
    except:
        return ''


def main():
    choice_input = raw_input(
        'Which kind of credentials would you like to use? [Default: 1]\n'
        '1. A comma-separated list of profiles that are all configured in ~/.aws/\n'
        '2. A single role name that I\'ve created in multiple accounts\n'
        '3. A list made up of all configured profiles in ~/.aws/\n'
    ) or '1'

    if choice_input == '1':
        accounts_input = raw_input('What are the names of these profiles?\n') or ''

        def get_ec2_client(account, region):
            return get_ec2_client_by_profile_name(account, region)

    elif choice_input == '2':
        role_name = raw_input('What is the name of this role? [Default: Administrator]\n') or 'Administrator'
        accounts_input = raw_input('What are the account IDs of these accounts?\n') or ''

        def get_ec2_client(account, region):
            return get_ec2_client_by_assumed_role(account, role_name, region)

    elif choice_input == '3':
        session = boto3.Session()
        accounts_input = ','.join(session.available_profiles)

        def get_ec2_client(account, region):
            return get_ec2_client_by_profile_name(account, region)

    else:
        raise Exception('Invalid choice')

    # Remove leading and trailing spaces from account names, just in case
    accounts = map(str.strip, accounts_input.split(','))

    if len(accounts) < 2:
        raise Exception('This is only interesting for multiple accounts. Please specify multiple accounts.')

    # Separate first account from the rest
    first_account, accounts = accounts[0], accounts[1:]

    # Get a list of all regions
    client = get_ec2_client(first_account, 'us-east-1')
    regions = sorted(get_regions(client))

    for region in regions:
        # Get AZs for specific region
        first_client = get_ec2_client(first_account, region)
        availability_zones = get_availabity_zones(first_client)

        for availability_zone in availability_zones:
            # Get offering ID for the first offering of the first account and find it in the other accounts
            offering_id = get_reserved_instances_offering_id(first_client, availability_zone)
            if offering_id:
                # Write output
                sys.stdout.write('\n' + offering_id + '\n')
                sys.stdout.write('---------------------------------\n')
                sys.stdout.write(first_account + ' | ' + availability_zone + '\n')

                for account in accounts:
                    client = get_ec2_client(account, region)
                    availability_zone = get_availability_zone_of_reserved_instance_offering(client, offering_id)

                    # Write output
                    sys.stdout.write(account + ' | ' + availability_zone + '\n')

                # Write output
                sys.stdout.write('---------------------------------\n')
                sys.stdout.flush()
            else:
                sys.stdout.write('\nNo reserved instance offering for ' + first_account + ' in ' + availability_zone + '\n')

if __name__ == '__main__':
    main()
