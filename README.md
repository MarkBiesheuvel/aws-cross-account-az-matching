# Matching EC2 Availability Zones Across AWS Accounts

This project is inspired by the article "Matching EC2 Availability Zones Across AWS Accounts" written by Eric Hammond.

https://alestic.com/2009/07/ec2-availability-zones/

## Background

> In order to prevent an overloading of a single availability zone when everybody tries to run their instances in us-east-1a, Amazon has added a layer of indirection so that each account’s availability zones can map to different physical data center equivalents.
>
> For example, zone `us-east-1a` in your account might be the same as zone `us-east-1c` in my account and `us-east-1d` in a third person’s account.

## How this script works?

This script takes two values as input; a list of account id for which you want to match availability zones and the name of a role which exists in all these accounts.

It is assumed that there is an aws profile configured which has permissions to `sts:AssumeRole` to this role in each account and that this role has at least permissions to `ec2:DescribeRegions`, `ec2:DescribeAvailabilityZones` and `ec2:DescribeReservedInstancesOfferings`.

Then the script will iterate over each availability zone in each region and search for a reserved instance offering. This offer will have an unique ID. Next it will look up this offer in all the other accounts and find out in which region this offer is in that account.

All of this is written to `stdout` and looks something like this:

```
05aae661-3154-4a28-97b0-dd87f6a53531
-------------+-------------------
111111111111 | ap-southeast-2a
222222222222 | ap-southeast-2b
333333333333 | ap-southeast-2a
-------------+-------------------

9b301a8b-f779-48fa-b2d3-140ed499b7e2
-------------+-------------------
111111111111 | ap-southeast-2b
222222222222 | ap-southeast-2a
333333333333 | ap-southeast-2b
-------------+-------------------

1ab91146-23f5-404b-833e-c46a1fbc2805
-------------+-------------------
111111111111 | ap-southeast-2c
222222222222 | ap-southeast-2c
333333333333 | ap-southeast-2c
-------------+-------------------
```

As you can see in the Sydney region availability zone `c` is the same across all 3 accounts, but account `222222222222` has available zone `a` and `b` switched around.
