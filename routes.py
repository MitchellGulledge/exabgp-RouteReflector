import requests
import json
import socket
from sys import stdout
import time
from netaddr import *

def get_summarized_office_prefixes():
    # obtaining json formatted list of all office 365 prefixes and URLs
    raw_office_prefixes = requests.get(
        "https://endpoints.office.com/endpoints/worldwide?clientrequestid=b10c5ed1-bad1-445f-b386-b919946339a7"
        ).content

    # converting contents variable from a bytes data type to json format
    formatted_office_prefixes = raw_office_prefixes.decode('utf8').replace("'", '"')

    # converting data type from string to json so we can iterate through the list for v4 addresses
    json_office_prefixes = json.loads(formatted_office_prefixes)

    # creating list for formatted IP addresses so we can later summarize the prefixes we advertise to Meraki
    unsummarized_list_of_formatted_prefixes = []

    for prefix in range(0, len(json_office_prefixes) -1):
        if 'ips' in json_office_prefixes[prefix]:
            for ip in json_office_prefixes[prefix]['ips']:
                if ':' not in ip:
                    # formatting ip prefix to an IPnetwork datatype to be summarized
                    formatted_ip = IPNetwork(ip)
                    # appending formatted ip to unsummarized_list_of_formatted_prefixes
                    unsummarized_list_of_formatted_prefixes.append(formatted_ip)
                    
    # summarizing the prefixes obtained after iterating through the unsummarized_list_of_formatted_prefixes
    finalized_prefix_list = cidr_merge(unsummarized_list_of_formatted_prefixes)

    # creating finalized prefix list for office traffic
    return(finalized_prefix_list)

def get_aws_prefixes():
    # obtaining json formatted list of all aws prefixes 
    raw_aws_json = requests.get(
        "https://ip-ranges.amazonaws.com/ip-ranges.json"
        ).content

    # converting contents variable from a bytes data type to json format
    formatted_aws_prefixes = raw_aws_json.decode('utf8').replace("'", '"')

    # converting list to json format
    json_aws_list = json.loads(formatted_aws_prefixes)

    # filtering json to only contain ipv4 prefixes
    aws_prefix_list = json_aws_list['prefixes']

    # creating temporary list to hold all the necessary AWS prefixes before being summarized
    unsummarized_list_of_formatted_prefixes = []

    # iterating through ipv4 prefixes to just show CIDR notation
    for prefix in aws_prefix_list:
        # creating an IPNetwork data type to append to the unsummarized_list_of_formatted_prefixes
        aws_prefix = IPNetwork(prefix['ip_prefix'])
        if str('us-') in str(prefix['region']):
            unsummarized_list_of_formatted_prefixes.append(aws_prefix)


    # summarizing list of IPv4 prefixes from AWS
    summarized_aws_prefixes = cidr_merge(unsummarized_list_of_formatted_prefixes)

    return(summarized_aws_prefixes)


def get_oracle_prefixes():
    # obtaining json formatted list of all oracle prefixes 
    raw_oracle_json = requests.get(
        "https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json"
        ).content

    # converting contents variable from a bytes data type to json format
    formatted_oracle_prefixes = raw_oracle_json.decode('utf8').replace("'", '"')

    # converting list to json format
    json_oracle_list = json.loads(formatted_oracle_prefixes)

    # filtering list to just get region information since thats where the CIDRs reside
    oracle_region_list = json_oracle_list['regions']

    # temp list to hold unsummarized list of oracle prefixes
    unsummarized_list_of_formatted_prefixes = []

    for prefix in oracle_region_list:
        # filtering out prefixes in the US for now since the test site is in the US
        if "us-" in str(prefix['region']):
            list_of_cidrs = prefix['cidrs']
            # iterating through the list of CIDRs for just the individual prefix 
            for ip_range in list_of_cidrs:
                oracle_ip_prefix = ip_range['cidr']
                # appending oracle_ip_prefix to unsummarized_list_of_formatted_prefixes
                unsummarized_list_of_formatted_prefixes.append(oracle_ip_prefix)

    # creating list of summarized oracle prefixes
    summarized_list_of_oracle_prefixes = cidr_merge(unsummarized_list_of_formatted_prefixes)

    return(summarized_list_of_oracle_prefixes)

office_ip_range = get_summarized_office_prefixes()
print("Number of Office Prefixes: " + str(len(office_ip_range)))

aws_ip_range = get_aws_prefixes()
print("Number of AWS Prefixes for North America: " + str(len(aws_ip_range)))

oracle_ip_range = get_oracle_prefixes()
print("Number of Oracle Prefixes for North America: " + str(len(oracle_ip_range)))

print(len(office_ip_range + aws_ip_range + oracle_ip_range))

# creating concatanated list of all saas prefixes
full_list_of_saas_prefixes = office_ip_range + aws_ip_range + oracle_ip_range

formatted_prefixes = str(full_list_of_saas_prefixes).replace("IPNetwork('","announce route ")
finalized_formatted_prefixes = str(formatted_prefixes).replace ("')", " next-hop 1.1.1.1" + '\n')
cleanup_prefixes = str(finalized_formatted_prefixes).replace(",","")
stdout.write(cleanup_prefixes[1:-1])
