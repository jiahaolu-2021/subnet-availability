#!/usr/bin/python3

import sys
import os
import subprocess
import pprint
import json
import re
import argparse

AWS_ENVS = ("devx", "qax", "stgx", "prod", "prod-eu")

# aws-keycloak -p admin-devx -- aws ec2 describe-subnets \
#                               --region us-east-1 \
#                               --filters "Name=vpc-id,Values=vpc-38b9b95f" \
#                               --query "Subnets[*].CidrBlock" \
#                               --output text

region = ""
GREEN = '\033[92m'
RESET = '\033[0m'

def get_subnet_id_list(env, vpc_id):
    cmd = 'aws-keycloak -p admin-{} -- aws ec2 describe-subnets --region {} --filters "Name=vpc-id,Values={}" --query "Subnets[*].SubnetId"'.format(
        env, region, vpc_id
    )

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    subnet_id_list_json_output = result.stdout

    try:
        parsed_subnet_id_list = json.loads(subnet_id_list_json_output)

        for subnet_id in parsed_subnet_id_list:
            get_detail_subnet_info(subnet_id)

    except json.JSONDecodeError as e:
        print(f"JSON decode error : {e}")


def get_detail_subnet_info(subnet_id):
    cmd = "aws-keycloak -p admin-{} -- aws ec2 describe-subnets --region {} --subnet-ids {} --query 'Subnets[0].{{CIDR: CidrBlock, AvailableIPs: AvailableIpAddressCount}}'".format(
        env, region, subnet_id
    )

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    detail_output_json = result.stdout

    try:
        detail_output = json.loads(detail_output_json)
        cidr = detail_output["CIDR"]
        availability = int(detail_output["AvailableIPs"])

        res = subprocess.run(
            "ipcalc {}".format(cidr), shell=True, capture_output=True, text=True
        )
        last_line = res.stdout.rstrip().split("\n")[-1]
        match = re.findall(r"\d+", last_line)
        capacity = int(match[0])
        print(
            f"{subnet_id} has {capacity} IPs in total, {availability} availabile ips, {GREEN}{availability/capacity:.0%} healthy {RESET}"
        )

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        detail_output = {}
        print("Failed to get subnet information")


# TODO: - add another parameter for specific subnet
# sample command: ./subnet.py devx vpc-38b9b95f
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the IP availability of a subnet")
    
    if len(sys.argv) < 3:
        print("Please provide env and vpc id")
        sys.exit(1)

    env = sys.argv[1]
    if env not in AWS_ENVS:
        print("Please provide a valid region")
        sys.exit(1)
    else:
        if env == "prod-eu":
            region = "eu-central-1"
        else:
            region = "us-east-1"

    vpc_id = sys.argv[2]

    if len(sys.argv) == 4:
        subnet_id = sys.argv[3]
        get_detail_subnet_info(subnet_id)
    else:
        get_subnet_id_list(env, vpc_id)
