#!/usr/bin/env python3

from __future__ import print_function

from sys import stdout
from time import sleep

import requests
import json
import socket
import datetime # make sure you update docker file with time
from netaddr import *

from collections import ChainMap

# ThousandEyes Credentials are placed below for obtaining agent to agent test info
root_url = ''
your_email = ''
your_apikey = ''

# aid is a param for API call - target account group - required to get the right agent back if you have multiple
your_aid = '' 

# see https://developer.thousandeyes.com/v6/agents/#/agents
# note - DESPITE documentation, API does not respect the agentType param - BOOOOO!
your_optional_payload = {'agentType':'Enterprise', 'aid' : your_aid}

# inputting BGP config for pop1 and pop2 neighbor IPs
pop1_bgp_neighbor_ip = '172.31.10.71'
pop2_bgp_neighbor_ip = '172.31.2.217'


# get agent to agent test list - ThousandEyes
def get_agent_to_agent_tests(email, api_token, payload):
    # performing get to obtain json of all agent to agent tests
    te_response = requests.get(f'{ root_url }/tests.json', auth=(email, api_token), \
        params=payload)

    # we want to convert to python dict first
    # otherwise you end up with double-encoded json (yep, I've seen this before)
    return json.loads(te_response.text)

# get test data from test ID - ThousandEyes
def get_test_data(time_start, time_end, test_id, email, api_token):
    # creating payload to include timestamp for obtaining test data
    # time_start and time_end variables must be in the ‘YYYY-mm-ddTHH:MM:SS’ format
    test_data_payload = {'agentType':'Enterprise', 'aid' : your_aid, \
    'from' : time_start,  'to' : time_end}
    # performing get to obtain json of all agent to agent tests
    te_test_data = requests.get(f'{ root_url }/net/metrics/'+str(test_id)+'.json', auth=(email, api_token), \
        params=test_data_payload)

    # we want to convert to python dict first
    # otherwise you end up with double-encoded json (yep, I've seen this before)
    return json.loads(te_test_data.text)

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

    # creating temporary list to hold all the necessary east us AWS prefixes before being summarized
    unsummarized_list_of_east_us_formatted_prefixes = []

    # creating temporary list to hold all the necessary west us AWS prefixes before being summarized
    unsummarized_list_of_west_us_formatted_prefixes = []

    # creating AWS dictionary to hold all region: prefixes so we can map test data to it later
    aws_data_dictionary = {}

    for prefix in json_aws_list['prefixes']:

        if prefix['region'] in aws_data_dictionary:

            aws_data_dictionary[prefix['region']].append(prefix['ip_prefix'])

        elif prefix['region'] not in aws_data_dictionary:

            # creating sample dictionary that is easy to later append to
            aws_data = {prefix['region']: [prefix['ip_prefix']]}

            aws_data_dictionary.update(aws_data)


    # creating AWS ThousandEyes Test Results Dictionary
    # Create your dictionary class  
    class my_dictionary(dict):  
    
        # __init__ function  
        def __init__(self):  
            self = dict()  
            
        # Function to add key:value  
        def add(self, key, value):  
            self[key] = value  
    
    # Main Function  
    dict_obj = my_dictionary() 


    # obtaining list of agent tests in AWS from ThousandEyes
    # Obtaining a list of current  agent to agent tests 
    te_agent_agent_tests_apicall = get_agent_to_agent_tests(email=your_email, api_token = your_apikey, \
        payload=your_optional_payload)

    # need to get current time for Thousandeyes test results (end time)
    test_end_time = datetime.datetime.now(datetime.timezone.utc)

    # need to obtain the test start delta of 5 min ago
    test_start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)

    # iterating through list of tests to filter for AWS specific tests
    for test in te_agent_agent_tests_apicall['test']:

        # filtering for tests that have AWS tesxt in the name
        if 'AWS' in str(test['testName']) and 'MMO' in str(test['testName']):


            for key in aws_data_dictionary:

                if str(key) in str(test['testName']):

                    if 'East US Agent' in str(test['testName']):

                        # pulling results for last 5 min on that specific test
                        east_us_test_data =  get_test_data(test_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), \
                            test_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), test['testId'], your_email, your_apikey)

                        for results in east_us_test_data['net']['metrics']:

                            if 'errorDetails' in results:

                                print("error detected")

                                continue

                            else:
                                # Taking input key = testname, value = averageLatency 
                                dict_obj.key = test['testName']
                                dict_obj.value = results['avgLatency']
                                
                                dict_obj.add(dict_obj.key, dict_obj.value)  
                              

                    elif 'West US Agent' in str(test['testName']):

                        # pulling results for last 5 min on that specific test
                        west_us_test_data =  get_test_data(test_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), \
                            test_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), test['testId'], your_email, your_apikey) 

                        for results in west_us_test_data['net']['metrics']:

                            if 'errorDetails' in results:

                                print("error detected")
                                
                                continue

                            else:
                                # Taking input key = testname, value = averageLatency 
                                dict_obj.key = test['testName']
                                dict_obj.value = results['avgLatency']
                                
                                dict_obj.add(dict_obj.key, dict_obj.value)  


    # creating 2 lists containing the prefixes advertised to pop1 + pop2
    pop1_east_us_hub_unsummarized_prefix_list = []
    pop2_west_us_hub_unsummarized_prefix_list = []


    # iterating through the regions in the azure_prefixes dictionary from the Azure json
    # splitting the iteration into a key value of region, prefix list
    for region, prefix_list in aws_data_dictionary.items():

        # creating 2 variables as placeholder for pop1 and pop2 test results
        east_region_test_results = ''
        west_region_test_results = ''

        for latency_results in dict_obj:

            # detecting if the region is inside the latency_results variable which is really the key 
            # value of the test results in the dict_obj that was used to build the thousandeyes 
            # data dictionary, there should be two matches for pop1 and pop2
            if str(region) in str(latency_results):

                # detecting the pop1 (East US Hub) in the latency_results (thousandeyes test name) 
                # variable, statically assigning 'East US Agent' but need to make pop1 variable
                if 'East US Agent' in str(latency_results):

                    east_region_test_results = dict_obj[latency_results]

                # detecting the pop2 (West US Hub) in the latency_results (thousandeyes test name) 
                # variable, statically assigning 'West US Agent' but need to make pop2 variable
                if 'West US Agent' in str(latency_results):

                    west_region_test_results = dict_obj[latency_results]

        if east_region_test_results != '' and west_region_test_results != '':

            if (east_region_test_results - west_region_test_results) > 20:
                
                print(str(region) + " prefixes will route to PoP2 (West US Hub)")

                pop2_west_us_hub_unsummarized_prefix_list = pop2_west_us_hub_unsummarized_prefix_list \
                    + aws_data_dictionary[region]

            elif (west_region_test_results - east_region_test_results) > 20:

                print(str(region) + " prefixes will route to PoP1 (East US Hub)")

                pop1_east_us_hub_unsummarized_prefix_list = pop1_east_us_hub_unsummarized_prefix_list \
                    + aws_data_dictionary[region]

            else:

                print(str(region) + " is within the 20ms deviation and will not be advertised")

    # summarizing list of IPv4 prefixes from GCP for east us
    summarized_east_aws_prefixes = cidr_merge(pop1_east_us_hub_unsummarized_prefix_list)

    # summarizing list of IPv4 prefixes from GCP for west us
    summarized_west_aws_prefixes = cidr_merge(pop2_west_us_hub_unsummarized_prefix_list)

    return [summarized_east_aws_prefixes, summarized_west_aws_prefixes]





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

    # temp list to hold unsummarized list of east us oracle prefixes
    unsummarized_list_of_east_us_formatted_prefixes = []

    # temp list to hold unsummarized list of west us oracle prefixes
    unsummarized_list_of_west_us_formatted_prefixes = []

    for prefix in oracle_region_list:
        # filtering out prefixes in the US for now since the test site is in the US
        if "us-ashburn" in str(prefix['region']):

            list_of_cidrs = prefix['cidrs']
            # iterating through the list of CIDRs for just the individual prefix 
            for ip_range in list_of_cidrs:
                oracle_ip_prefix = ip_range['cidr']
                # appending oracle_ip_prefix to unsummarized_list_of_east_us_formatted_prefixes
                unsummarized_list_of_east_us_formatted_prefixes.append(oracle_ip_prefix)

        elif 'us-phoenix' in str(prefix['region']) or 'us-sanjose'in str(prefix['region']):

            list_of_cidrs = prefix['cidrs']
            # iterating through the list of CIDRs for just the individual prefix 
            for ip_range in list_of_cidrs:
                oracle_ip_prefix = ip_range['cidr']
                # appending oracle_ip_prefix to unsummarized_list_of_west_us_formatted_prefixes
                unsummarized_list_of_west_us_formatted_prefixes.append(oracle_ip_prefix)


    # creating list of summarized east us oracle prefixes
    summarized_list_of_east_us_oracle_prefixes = cidr_merge(unsummarized_list_of_east_us_formatted_prefixes)

    # creating list of summarized west us oracle prefixes
    summarized_list_of_west_us_oracle_prefixes = cidr_merge(unsummarized_list_of_west_us_formatted_prefixes)

    return [summarized_list_of_west_us_oracle_prefixes, summarized_list_of_east_us_oracle_prefixes]




def get_gcp_prefixes():

    # obtaining json formatted list of all GCP prefixes 
    raw_gcp_json = requests.get(
        "https://www.gstatic.com/ipranges/cloud.json"
        ).content

    # converting contents variable from a bytes data type to json format
    formatted_gcp_prefixes = raw_gcp_json.decode('utf8').replace("'", '"')

    # converting list to json format
    json_gcp_list = json.loads(formatted_gcp_prefixes)

    # creating 2 lists containing the prefixes advertised to pop1 + pop2
    pop1_east_us_hub_unsummarized_prefix_list = []
    pop2_west_us_hub_unsummarized_prefix_list = []
    
    # Main Function  
    gcp_prefixes = []

    # iterating through ipv4 prefixes to just show CIDR notation 
    # (filtering for v4 only by specifying prefixes)
    for prefix in json_gcp_list['prefixes']:

        if 'ipv4Prefix' in prefix:

            # Taking input key = testname, value = averageLatency 
            gcp_prefixes.append({"region": prefix['scope'], "prefix": [prefix['ipv4Prefix']]})

    # creating dictionary of all key values to later append to
    gcp_prefixes_dictionary = {}
    for data in gcp_prefixes:

        if data['region'] not in gcp_prefixes_dictionary:
           
            gcp_prefixes_dictionary.update({data['region']: []})

    for regions in gcp_prefixes:


        for individual_prefixes in gcp_prefixes_dictionary:

            if regions['region'] in str(individual_prefixes):

                gcp_prefixes_dictionary[regions['region']].append(str(regions['prefix'])[2:-2])
    
    # creating GCP ThousandEyes Test Results Dictionary
    # Create your dictionary class  
    class my_dictionary(dict):  
    
        # __init__ function  
        def __init__(self):  
            self = dict()  
            
        # Function to add key:value  
        def add(self, key, value):  
            self[key] = value  
    
    # Main Function  
    dict_obj = my_dictionary() 

    # obtaining list of agent tests in GCP from ThousandEyes
    # Obtaining a list of current  agent to agent tests 
    te_agent_agent_tests_apicall = get_agent_to_agent_tests(email=your_email, api_token = your_apikey, \
        payload=your_optional_payload)

    # need to get current time for Thousandeyes test results (end time)
    test_end_time = datetime.datetime.now(datetime.timezone.utc)

    # need to obtain the test start delta of 5 min ago
    test_start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)

    # iterating through list of tests to filter for GCP specific tests
    for test in te_agent_agent_tests_apicall['test']:

        # filtering for tests that have GCP tesxt in the name
        if 'GCP' in str(test['testName']) and 'MMO' in str(test['testName']):

            for key in gcp_prefixes_dictionary:

                if str(key) in str(test['testName']):

                    if 'East US Agent' in str(test['testName']):

                        # pulling results for last 5 min on that specific test
                        east_us_test_data =  get_test_data(test_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), \
                            test_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), test['testId'], your_email, your_apikey)

                        for results in east_us_test_data['net']['metrics']:

                            if 'errorDetails' in results:

                                print("error detected")

                                continue

                            else:
                                # Taking input key = testname, value = averageLatency 
                                dict_obj.key = test['testName']
                                dict_obj.value = results['avgLatency']
                                
                                dict_obj.add(dict_obj.key, dict_obj.value)  
                              

                    elif 'West US Agent' in str(test['testName']):

                        # pulling results for last 5 min on that specific test
                        west_us_test_data =  get_test_data(test_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), \
                            test_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), test['testId'], your_email, your_apikey) 

                        for results in west_us_test_data['net']['metrics']:

                            if 'errorDetails' in results:

                                print("error detected")
                                
                                continue

                            else:
                                # Taking input key = testname, value = averageLatency 
                                dict_obj.key = test['testName']
                                dict_obj.value = results['avgLatency']
                                
                                dict_obj.add(dict_obj.key, dict_obj.value)  


    # creating 2 lists containing the prefixes advertised to pop1 + pop2
    pop1_east_us_hub_unsummarized_prefix_list = []
    pop2_west_us_hub_unsummarized_prefix_list = []


    # iterating through the regions in the azure_prefixes dictionary from the Azure json
    # splitting the iteration into a key value of region, prefix list
    for region, prefix_list in gcp_prefixes_dictionary.items():

        # creating 2 variables as placeholder for pop1 and pop2 test results
        east_region_test_results = ''
        west_region_test_results = ''

        for latency_results in dict_obj:

            # detecting if the region is inside the latency_results variable which is really the key 
            # value of the test results in the dict_obj that was used to build the thousandeyes 
            # data dictionary, there should be two matches for pop1 and pop2
            if str(region) in str(latency_results):

                # detecting the pop1 (East US Hub) in the latency_results (thousandeyes test name) 
                # variable, statically assigning 'East US Agent' but need to make pop1 variable
                if 'East US Agent' in str(latency_results):

                    east_region_test_results = dict_obj[latency_results]

                # detecting the pop2 (West US Hub) in the latency_results (thousandeyes test name) 
                # variable, statically assigning 'West US Agent' but need to make pop2 variable
                if 'West US Agent' in str(latency_results):

                    west_region_test_results = dict_obj[latency_results]

        if east_region_test_results != '' and west_region_test_results != '':

            if (east_region_test_results - west_region_test_results) > 20:
                
                print(str(region) + " prefixes will route to PoP2 (West US Hub)")

                pop2_west_us_hub_unsummarized_prefix_list = pop2_west_us_hub_unsummarized_prefix_list \
                    + gcp_prefixes_dictionary[region]

            elif (west_region_test_results - east_region_test_results) > 20:

                print(str(region) + " prefixes will route to PoP1 (East US Hub)")

                pop1_east_us_hub_unsummarized_prefix_list = pop1_east_us_hub_unsummarized_prefix_list \
                    + gcp_prefixes_dictionary[region]

            else:

                print(str(region) + " is within the 20ms deviation and will not be advertised")


    # summarizing list of IPv4 prefixes from GCP for east us
    summarized_east_gcp_prefixes = cidr_merge(pop1_east_us_hub_unsummarized_prefix_list)

    # summarizing list of IPv4 prefixes from GCP for west us
    summarized_west_gcp_prefixes = cidr_merge(pop2_west_us_hub_unsummarized_prefix_list)

    return [summarized_east_gcp_prefixes, summarized_west_gcp_prefixes]




def get_azure_prefixes():

    # performing request to obtain a json of all the azure prefixes per region in json format
    raw_azure_json = requests.get(
        "https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_20210104.json"
        ).content


    # converting contents variable from a bytes data type to json format
    formatted_azure_prefixes = raw_azure_json.decode('utf8').replace("'", '"')

    # converting list to json format
    json_azure_list = json.loads(formatted_azure_prefixes)

    # creating a dictionary to hold a dictionary with a key value pair of region/prefixes
    azure_prefixes = {}

    # iterating through json to match prefixes based on region of ThousandEyes Test
    for prefix in json_azure_list['values']:

        # ensuring that the region key exists 
        # (not going to track the global prefixes that arent bound to a region)
        if prefix['properties']['region']:
            if not prefix['properties']['region'] in azure_prefixes:
                azure_prefixes[prefix['properties']['region']] = []

            for ip_prefix in prefix['properties']['addressPrefixes']:
                if ':' not in ip_prefix:
                    azure_prefixes[
                        prefix['properties']['region']
                    ].append(
                        ip_prefix
                    )


    # creating Azure ThousandEyes Test Results Dictionary
    # Create your dictionary class  
    class my_dictionary(dict):  
    
        # __init__ function  
        def __init__(self):  
            self = dict()  
            
        # Function to add key:value  
        def add(self, key, value):  
            self[key] = value  
    
    # Main Function  
    dict_obj = my_dictionary()  

    # obtaining list of agent tests in Azure from ThousandEyes
    # Obtaining a list of current  agent to agent tests 
    te_agent_agent_tests_apicall = get_agent_to_agent_tests(email=your_email, api_token = your_apikey, \
        payload=your_optional_payload)

    # need to get current time for Thousandeyes test results (end time)
    test_end_time = datetime.datetime.now(datetime.timezone.utc)

    # need to obtain the test start delta of 5 min ago
    test_start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)

    # iterating through list of tests to filter for Azure specific tests
    for test in te_agent_agent_tests_apicall['test']:

        # filtering for tests that have Azure tesxt in the name
        if 'Azure' in str(test['testName']) and 'MMO' in str(test['testName']):

            # iterating through Azure prefixes dictionary per region
            for region in azure_prefixes:

                # matching testname based on Azure region
                if str(region) in str(test['testName']):

                    # creating placeholder variable for the time stamp
                    te_test_time = datetime.datetime.now(datetime.timezone.utc) - \
                        datetime.timedelta(minutes=300)

                    # matching East US Hub results in the name
                    if 'East US Agent' in str(test['testName']):

                        # pulling results for last 5 min on that specific test
                        east_us_test_data =  get_test_data(test_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), \
                            test_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), test['testId'], your_email, your_apikey)

                        for results in east_us_test_data['net']['metrics']:

                            if 'errorDetails' in results:

                                print("error detected")

                                continue

                            else:
                                # Taking input key = testname, value = averageLatency 
                                dict_obj.key = test['testName']
                                dict_obj.value = results['avgLatency']
                                
                                dict_obj.add(dict_obj.key, dict_obj.value)  
                              

                    elif 'West US Agent' in str(test['testName']):

                        # pulling results for last 5 min on that specific test
                        west_us_test_data =  get_test_data(test_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), \
                            test_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"), test['testId'], your_email, your_apikey) 

                        for results in west_us_test_data['net']['metrics']:

                            if 'errorDetails' in results:

                                print("error detected")
                                
                                continue

                            else:
                                # Taking input key = testname, value = averageLatency 
                                dict_obj.key = test['testName']
                                dict_obj.value = results['avgLatency']
                                
                                dict_obj.add(dict_obj.key, dict_obj.value)  

    # creating 2 lists containing the prefixes advertised to pop1 + pop2
    pop1_east_us_hub_unsummarized_prefix_list = []
    pop2_west_us_hub_unsummarized_prefix_list = []


    # iterating through the regions in the azure_prefixes dictionary from the Azure json
    # splitting the iteration into a key value of region, prefix list
    for region, prefix_list in azure_prefixes.items():

        east_region_test_results = ''
        west_region_test_results = ''

        for latency_results in dict_obj:

            # detecting if the region is inside the latency_results variable which is really the key 
            # value of the test results in the dict_obj that was used to build the thousandeyes 
            # data dictionary, there should be two matches for pop1 and pop2
            if str(region) in str(latency_results):

                # detecting the pop1 (East US Hub) in the latency_results (thousandeyes test name) 
                # variable, statically assigning 'East US Agent' but need to make pop1 variable
                if 'East US Agent' in str(latency_results):

                    east_region_test_results = dict_obj[latency_results]

                # detecting the pop2 (West US Hub) in the latency_results (thousandeyes test name) 
                # variable, statically assigning 'West US Agent' but need to make pop2 variable
                if 'West US Agent' in str(latency_results):

                    west_region_test_results = dict_obj[latency_results]

        if east_region_test_results != '' and west_region_test_results != '':

            if (east_region_test_results - west_region_test_results) > 20:
                
                print(str(region) + " prefixes will route to PoP2 (West US Hub)")

                pop2_west_us_hub_unsummarized_prefix_list = pop2_west_us_hub_unsummarized_prefix_list \
                    + azure_prefixes[region]

            elif (west_region_test_results - east_region_test_results) > 20:

                print(str(region) + " prefixes will route to PoP1 (East US Hub)")

                pop1_east_us_hub_unsummarized_prefix_list = pop1_east_us_hub_unsummarized_prefix_list \
                    + azure_prefixes[region]

            else:

                print(str(region) + " is within the 20ms deviation and will not be advertised")

    pop1_east_us_hub_summarized_prefix_list = cidr_merge(pop1_east_us_hub_unsummarized_prefix_list)
    pop2_west_us_hub_summarized_prefix_list = cidr_merge(pop2_west_us_hub_unsummarized_prefix_list)

    # known issue of westus/2 not being picked up in loop since testname doesnt match region exactly
    return [pop1_east_us_hub_summarized_prefix_list, pop2_west_us_hub_summarized_prefix_list]


azure_ip_range = get_azure_prefixes()
#print("Number of West US Azure Prefixes: " + str(len(azure_ip_range[0])))
#print("Number of East US Azure Prefixes: " + str(len(azure_ip_range[1])))

gcp_ip_range = get_gcp_prefixes()
#print("Number of West US GCP Prefixes: " + str(len(gcp_ip_range[0])))
#print("Number of East US GCP Prefixes: " + str(len(gcp_ip_range[1])))

aws_ip_range = get_aws_prefixes()

#oracle_ip_range = get_oracle_prefixes()
#print("Number of West US Oracle Prefixes: " + str(len(oracle_ip_range[0])))
#print("Number of East US Oracle Prefixes: " + str(len(oracle_ip_range[1])))

# Creating list for each BGP neighbor to later announce/withdraw the prefixes from
west_us_prefix_list = azure_ip_range[0] + gcp_ip_range[0] + aws_ip_range[0] 
east_us_prefix_list = azure_ip_range[1] + gcp_ip_range[1] + aws_ip_range[1] 

print(len(east_us_prefix_list))
print(len(west_us_prefix_list))

formatted_pop1_prefixes = str(east_us_prefix_list).replace("IPNetwork('","neighbor "+ \
    str(pop1_bgp_neighbor_ip) +" announce route ")
finalized_pop1_formatted_prefixes = str(formatted_pop1_prefixes).replace ("')", " next-hop 172.31.0.1" + '\n')


pop1_list = list(finalized_pop1_formatted_prefixes.split(","))

formatted_pop2_prefixes = str(west_us_prefix_list).replace("IPNetwork('","neighbor " + str(pop2_bgp_neighbor_ip) + " announce route ")
finalized_pop2_formatted_prefixes = str(formatted_pop2_prefixes).replace ("')", " next-hop 172.31.0.1" + '\n')


pop2_list = list(finalized_pop2_formatted_prefixes.split(","))

# leaving for future reference
#messages = [
#    'announce route 100.10.0.0/24 next-hop self',
#    'announce route 200.20.0.0/24 next-hop self',
#]

sleep(5)

#Iterate through messages
for message in pop1_list:
    stdout.write(str(message)[1:-1] + '\n')
    stdout.flush()
    #sleep(1)

sleep(5)

#Iterate through messages
for message in pop2_list:
    stdout.write(str(message)[1:-1] + '\n')
    stdout.flush()
    #sleep(1)


#Loop endlessly to allow ExaBGP to continue running
while True:
    sleep(1)
