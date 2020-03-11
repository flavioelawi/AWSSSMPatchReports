This is a very simple script to help you build a CSV report from the AWS SSM Patch Inventory.

To use it you will need:

* Python > 3.6
* Boto3

After you have installed Python, you will have to install the dependencies:

```
pip install -r REQUIREMENTS.txt
```

To execute the script:

```
python ssm_patch_report.py -r us-east-1 -o /tmp/my_account_patch_compliance.csv
```

Usage:

```
usage: patch_report.py [-h] -r REGION -o OUT_FILE
ssm_patch_report.py: error: the following arguments are required: -r/--region, -o/--out-file
```