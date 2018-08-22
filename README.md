# Matching EC2 Availability Zones Across AWS Accounts

This project is inspired by the article "Matching EC2 Availability Zones Across AWS Accounts" written by Eric Hammond.

https://alestic.com/2009/07/ec2-availability-zones/

## Background

> In order to prevent an overloading of a single availability zone when everybody tries to run their instances in us-east-1a, Amazon has added a layer of indirection so that each account’s availability zones can map to different physical data center equivalents.  Additionally, not all accounts have access to all availability zones.  For example, newer accounts often don't having access to older AZs in a region.  This allows accounts already established in those older AZs to continue to be able to create new instances there.
>
> For example, zone `us-east-1a` in your account might be the same as zone `us-east-1c` in my account and `us-east-1d` in a third person’s account, while a fourth account might not even see that AZ at all.

Amazon's webpage [Regions and Availability Zones](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html) says this:

> An Availability Zone is represented by a region code followed by a letter identifier; for example, `us-east-1a`. To ensure that resources are distributed across the Availability Zones for a region, we independently map Availability Zones to identifiers for each account. For example, your Availability Zone `us-east-1a` might not be the same location as `us-east-1a` for another account.
>
> As Availability Zones grow over time, our ability to expand them can become constrained. If this happens, we might restrict you from launching an instance in a constrained Availability Zone unless you already have an instance in that Availability Zone. Eventually, we might also remove the constrained Availability Zone from the list of Availability Zones for new customers. Therefore, your account might have a different number of available Availability Zones in a region than another account.

## What does this script do?

This script does not correlate AZs in each account to Amazon's physical availability zone mapping.  It is not possible to do this.  Instead, the script correlates the AZ across accounts to each other and then tells you how the AZ mapping in each account matches to that of other accounts.

## How does this script work?

This script has three different modes of operation:

1. It can take a list of account IDs to match availability zones across and the name of a role that exists in all of those accounts. It is assumed that there is an aws profile configured which has permissions to `sts:AssumeRole` to this role in each account and that this role has at least permissions to `ec2:DescribeRegions`, `ec2:DescribeAvailabilityZones` and `ec2:DescribeReservedInstancesOfferings`.
2. It can take a list of account IDs for which credentials have been configured in files in `~/.aws/`
3. It can use all accounts for which credentials have been configured in files in `~/.aws/`

The script iterates over each availability zone in each region and searches for a reserved instance offering. This offer will have an unique ID. Next it will look up this offer in all of the other accounts and find out in which region this offer is in that account.  Since the offer ID for reserved instances seems to be the same across accounts, this allows one to correlate AZs between accounts.

All of this is written to `stdout` and looks something like this:

```
Mapping for region ap-northeast-1
+-----------------+---+---+---+---+
| xxxxxxxxxxxxx   | a | . | c | d |
| yyyyyyyyyyyyyyy | a | b | c | d |
| zzzzzzzzzzzzz   | a | . | c | d |
+-----------------+---+---+---+---+

Mapping for region eu-central-1
+-----------------+---+---+---+
| xxxxxxxxxxxxx   | a | b | c |
| yyyyyyyyyyyyyyy | a | b | c |
| zzzzzzzzzzzzz   | a | b | c |
+-----------------+---+---+---+

Mapping for region eu-west-1
+-----------------+---+---+---+
| xxxxxxxxxxxxx   | a | b | c |
| yyyyyyyyyyyyyyy | b | c | a |
| zzzzzzzzzzzzz   | c | a | b |
+-----------------+---+---+---+
```
In the Tokyo region (`ap-northeast-1`), only account `yyyyyyyyyyyyyyy` has access to AZ `b`.  The other accounts don't have access to that AZ, at least regarding reserved instances.  For the other three AZs that are accessible to all three accounts, they have the same mapping across the three accounts.

In the Frankfurt region (`eu-central-1`) the letter `a`, `b`, and `c` all map to the same AZs across the three example accounts.

In the Ireland region (`eu-west-1`) the letter `a` in account `xxxxxxxxxxxxx` is the same AZ is letter `b` in account `yyyyyyyyyyyyyyy` and `c` in account `zzzzzzzzzzzzz`.
