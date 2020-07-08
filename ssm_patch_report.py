import csv
import boto3
import argparse
import sys
import logging
import datetime
from datetime import timezone

from botocore.exceptions import NoCredentialsError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


LATEST_INSTALL_TIME_KEY = "LatestInstalledTime"
ACCOUNT_ID_KEY = "AccountId"
REGION_KEY = "Region"
INSTANCE_ID_KEY = "InstanceId"
MISSING_PATCHES_COUNT_KEY = "MissingPatchesCount"

MISSING_PATCH_STATE = "Missing"


def main(region: str, out_file: str, with_tags: bool):
    CSV_FIELDS = [
        ACCOUNT_ID_KEY,
        REGION_KEY,
        INSTANCE_ID_KEY,
        MISSING_PATCHES_COUNT_KEY,
        LATEST_INSTALL_TIME_KEY
    ]
    ec2 = boto3.client("ec2", region_name=region)
    sts = boto3.client("sts")
    try:
        account_id = sts.get_caller_identity().get("Account")
    except NoCredentialsError as e:
        logger.critical("Sorry, I could not find credentials.")
        sys.exit(1)
    
    reservations = ec2.describe_instances().get("Reservations", None)
    instances = []
    for reservation in reservations:
        instances.extend(reservation.get("Instances", None))

    for instance in instances:
        logger.info(f"Checking {instance['InstanceId']}")
        instance[ACCOUNT_ID_KEY] = account_id
        instance[REGION_KEY] = region
        instance[MISSING_PATCHES_COUNT_KEY] = 0
        instance["InstalledPatchesCount"] = 0
        instance = _get_instance_patches(instance, region)
        if instance.get("Tags") and with_tags:
            instance["Tags"] = _transform_instance_tags(instance.get("Tags"))
            instance.update(instance["Tags"])
            CSV_FIELDS.extend([k for k, v in instance["Tags"].items()])
            CSV_FIELDS = list(set(CSV_FIELDS))
        logger.info(f"Finished instance {instance[INSTANCE_ID_KEY]}")
    csv_file = open(out_file, "w")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(instances)
    csv_file.close()

def _get_instance_patches(instance: dict, region: str) -> dict:
    ssm = boto3.client("ssm", region_name=region)
    paginator = ssm.get_paginator("describe_instance_patches")
    page_iterator = paginator.paginate(
        InstanceId=instance[INSTANCE_ID_KEY]
    )
    latest_install_date = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
    instance["Patches"] = []
    for page in page_iterator:
        for patch in page["Patches"]:
            if patch["State"] == MISSING_PATCH_STATE:
                instance[MISSING_PATCHES_COUNT_KEY] += 1
            else:
                instance["InstalledPatchesCount"] += 1
                if patch["InstalledTime"] > latest_install_date:
                    latest_install_date = patch["InstalledTime"]
        instance["Patches"].extend(page["Patches"])
        instance[LATEST_INSTALL_TIME_KEY] = latest_install_date
    return instance

def _transform_instance_tags(tags: list=None):
    if tags is None:
        return
    _tags = {}
    for tag in tags:
        _tags[tag["Key"]] = tag["Value"]
    return _tags

if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("-r", "--region", dest="region", required=True, help="The region for which to query the SSM Patch Inventory.")
    parser.add_argument("-o", "--out-file", dest="out_file", required=True, help="The destination CSV file path.")
    parser.add_argument("-t", "--with-tags", dest="with_tags", action="store_const", const="True", required=False, help="Add instance tags to the report.")
    args = parser.parse_args()
    main(args.region, args.out_file, args.with_tags)
