import csv
import boto3
import argparse
import sys
from botocore.exceptions import NoCredentialsError

CSV_FIELDS = [
    "AccountId",
    "Region",
    "InstanceId",
    "MissingPatchesCount"
]

MISSING_PATCH_STATE = "Missing"


def main(region: str, out_file: str):
    try:
        ec2 = boto3.client("ec2", region_name=region)
        ssm = boto3.client("ssm", region_name=region)
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity().get("Account")
    except NoCredentialsError as e:
        print(f"Sorry, I could not find credentials, Exception: {e}")
        sys.exit(1)
    reservations = ec2.describe_instances().get("Reservations", None)
    instances = []
    for reservation in reservations:
        instances.extend(reservation.get("Instances", None))

    for instance in instances:
        instance["AccountId"] = account_id
        instance["Region"] = region
        instance["MissingPatchesCount"] = 0
        instance["InstalledPatchesCount"] = 0
        instance["Patches"] = []
        paginator = ssm.get_paginator("describe_instance_patches")
        page_iterator = paginator.paginate(
            InstanceId=instance["InstanceId"]
        )
        for page in page_iterator:
            for patch in page["Patches"]:
                if patch["State"] == MISSING_PATCH_STATE:
                    instance["MissingPatchesCount"] += 1
                else:
                    instance["InstalledPatchesCount"] += 1
            instance["Patches"].extend(page["Patches"])
    
    csv_file = open(out_file, "w")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(instances)
    csv_file.close()

    return



if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("-r", "--region", dest="region", required=True, help="The region for which to query the SSM Patch Inventory.")
    parser.add_argument("-o", "--out-file", dest="out_file", required=True, help="The destination CSV file path.")
    args = parser.parse_args()
    main(args.region, args.out_file)
