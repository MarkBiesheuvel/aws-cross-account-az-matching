#!/bin/python
import boto3

# Search for reserved instances for this instance type.  Not all AZs have instances of
# every instance type available for reservation.  By picking a very common type, we sidestep
# that problem.  Other instance types (like m4.* or m5.*) aren't available in every AZ.
INSTANCE_TYPE = 't2.large'


class Account:

    def __init__(self, account_id=None, role_name=None, profile_name=None):
        if profile_name is not None:
            self.initialize_by_profile_name(profile_name)
        elif account_id is not None and role_name is not None:
            self.initialize_by_assume_role(account_id, role_name)
        else:
            raise Exception('Missing parameters for Account')

    def initialize_by_profile_name(self, profile_name):
        # Store account name
        self.name = profile_name

        # Create boto3 client by using a profile name
        self.session = boto3.Session(profile_name=profile_name)

    def initialize_by_assume_role(self, account_id, role_name):
        # Store account name
        self.name = account_id

        # Create an STS client object that represents a live connection to the
        # STS service.
        client = boto3.client('sts')

        # Call the assume_role method of the STSConnection object and pass the role
        # ARN and a role session name.
        response = client.assume_role(
            RoleArn='arn:aws:iam::%{}:role/{}'.format(account_id, role_name),
            RoleSessionName='session'
        )

        credentials = response['Credentials']

        # Create boto3 client by using assumed credentials from sts
        self.session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

    def get_ec2_client(self, region):
        return self.session.client('ec2', region_name=region)

    def get_regions(self):
        response = self.get_ec2_client('us-east-1').describe_regions()
        regions = [
            region['RegionName']
            for region in response['Regions']
        ]
        return sorted(regions)

    def get_availabity_zones(self, region):
        response = self.get_ec2_client(region).describe_availability_zones(
            Filters=[
                {
                    'Name': 'state',
                    'Values': [
                        'available'
                    ]
                }
            ]
        )
        return [
            az['ZoneName']
            for az in response['AvailabilityZones']
        ]

    def get_reserved_instances_offering_id(self, region, availability_zone):
        try:
            response = self.get_ec2_client(region).describe_reserved_instances_offerings(
                AvailabilityZone=availability_zone,
                IncludeMarketplace=False,
                InstanceType=INSTANCE_TYPE,
                MaxResults=1,
            )

            offerings = response['ReservedInstancesOfferings']

            if len(offerings) == 0:
                return None

            return offerings[0]['ReservedInstancesOfferingId']
        except:
            return None

    def get_availability_zone_of_reserved_instance_offering(self, region, offering_id):
        try:
            response = self.get_ec2_client(region).describe_reserved_instances_offerings(
                ReservedInstancesOfferingIds=[
                    offering_id
                ],
                MaxResults=1,
            )

            offerings = response['ReservedInstancesOfferings']

            if len(offerings) == 0:
                return None

            return offerings[0]['AvailabilityZone']
        except:
            return None


def get_accounts_from_input():
    choice_input = raw_input(
        'Which kind of credentials would you like to use? [Default: 1]\n'
        '1. A comma-separated list of profiles that are all configured in ~/.aws/\n'
        '2. A single role name that I\'ve created in multiple accounts\n'
        '3. A list made up of all configured profiles in ~/.aws/\n'
    ) or '1'

    if choice_input == '1':
        profiles = raw_input('What are the names of these profiles?\n') or ''

        # Remove leading and trailing spaces from account names, just in case
        profiles = [
            profile.strip()
            for profile in profiles.split(',')
        ]

        # Map profiles to sessions
        return [
            Account(profile_name=profile)
            for profile in profiles
        ]

    elif choice_input == '2':
        role_name = raw_input('What is the name of this role? [Default: Administrator]\n') or 'Administrator'
        account_ids = raw_input('What are the account IDs of these accounts?\n') or ''

        # Remove leading and trailing spaces from account names, just in case
        account_ids = [
            account_id.strip()
            for account_id in account_ids.split(',')
        ]

        # Map accounts to sessions by assuming role into the accounts
        return [
            Account(account_id=account_id, role_name=role_name)
            for account_id in account_ids
        ]

    elif choice_input == '3':
        session = boto3.Session()

        # Map profiles to sessions
        return [
            Account(profile_name=profile)
            for profile in session.available_profiles
        ]
    else:
        raise Exception('Invalid choice')


def print_dictionary(region, az_dictionary, max_account_name_length):
    seperator = '+-{}-+{}'.format(
        '-' * max_account_name_length,
        '---+' * len(az_dictionary.values()[0]),
    )

    # Dump output for this region
    print('Mapping for region {}'.format(region))
    print(seperator)

    for account_name in az_dictionary:
        azs = az_dictionary[account_name]
        print('| {0:{1}} | {2} |'.format(
            account_name,
            max_account_name_length,
            ' | '.join(azs),
        ))

    print(seperator)
    print('')


def main():
    accounts = get_accounts_from_input()

    # Create newline after input
    print('')

    if len(accounts) < 2:
        raise Exception('This is only interesting for multiple accounts. Please specify multiple accounts.')

    # Separate first account from the rest
    first_account, other_accounts = accounts[0], accounts[1:]

    # Calculcate the longest account name
    max_account_name_length = max([len(account.name) for account in accounts])

    # Get a list of all regions
    regions = first_account.get_regions()

    for region in regions:
        # Get AZs for specific region
        availability_zones = first_account.get_availabity_zones(region)

        # Initialize our dictionary of lists for the current region
        az_dictionary = {
            account.name: []
            for account in accounts
        }

        for availability_zone in availability_zones:
            az_dictionary[first_account.name].append(availability_zone[-1:])

            # Get offering ID for the first offering of the first account and find it in the other accounts
            offering_id = first_account.get_reserved_instances_offering_id(region, availability_zone)

            if offering_id is not None:
                for other_account in other_accounts:
                    az2 = other_account.get_availability_zone_of_reserved_instance_offering(region, offering_id)

                    az_dictionary[other_account.name].append(az2[-1:] if az2 is not None else '?')

        print_dictionary(region, az_dictionary, max_account_name_length)


if __name__ == '__main__':
    main()
