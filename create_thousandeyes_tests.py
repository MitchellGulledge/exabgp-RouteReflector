import requests
import json

root_url = 'https://api.thousandeyes.com/v6'
your_email = ''
your_apikey = ''
west_us_agent_name = '' # fill in agent name
east_us_agent_name = '' # fill in agent name
west_us_agent_id = ''
east_us_agent_id = ''

# aid is a param for API call - target account group - required to get the right agent back if you have multiple
your_aid = '199526' 

# see https://developer.thousandeyes.com/v6/agents/#/agents
# note - DESPITE documentation, API does not respect the agentType param - BOOOOO!
your_optional_payload = {'agentType':'Enterprise', 'aid' : your_aid}

# get agents
def get_agents(email, api_token, payload):
    # make our Python requests module request with HTTP GET, URL, params, & basic auth
    # (see request documentation + thousandEyes URL above for details)
    te_response = requests.get(f'{ root_url }/agents.json', auth=(email, api_token), params=payload)

    # we want to convert to python dict first
    # otherwise you end up with double-encoded json (yep, I've seen this before)
    return json.loads(te_response.text)

# get agent to agent test list
def get_agent_to_agent_tests(email, api_token, payload):
    # performing get to obtain json of all agent to agent tests
    te_response = requests.get(f'{ root_url }/tests.json', auth=(email, api_token), \
        params=payload)

    # we want to convert to python dict first
    # otherwise you end up with double-encoded json (yep, I've seen this before)
    return json.loads(te_response.text)


# creating function to delete stale tests
def delete_stale_tests(email, api_token, payload, test_id):
    # post to delete agent to agent tests
    te_delete_test_response = requests.post(f'{ root_url }/tests/agent-to-agent/'+ str(test_id) \
        +'/delete', auth=(email, api_token), params=payload)

    return te_delete_test_response

# function to remove values from a list
def remove_values_from_list(the_list, val):
    # using list comprehension to filter unwanted values
   return [value for value in the_list if value != val]

# function to create new agent to agent test with variables
def create_agent_to_agent_test(email, api_token, payload, body):

    te_create_test_response = requests.post(f'{ root_url }/tests/agent-to-agent/new.json', \
        auth=(email, api_token), params=payload, data = body, headers = {"Content-Type" : "application/json"})

    return json.loads(te_create_test_response.text)
    


# call our function and we get a dict back 
te_apicall = get_agents(email=your_email, api_token=your_apikey, payload=your_optional_payload)

# te_apicall is now a dict that we can work with
# dump it to JSON (or iterate over it as a Python dict to filter by keys/values)
pretty_print = json.dumps(te_apicall, indent=4, sort_keys=False)

# creating list to iterate through to match based on country ID
agent_list = te_apicall['agents']

# creating a variable that will become list of Azure agent IDs we want the enterprise client to hit
azure_destination_agent_list = []

# creating a variable that will become list of AWS agent IDs we want the enterprise client to hit
aws_destination_agent_list = []

# creating a variable that will become list of GCP agent IDs we want the enterprise client to hit
gcp_destination_agent_list = []


# iterating through the agent list to match all endpoints in the location New York Area
for agents in agent_list:
    # Matching all agents in the new york area on location key 
    # Filtering out IPv6 due to lack of support on Umbrella + Meraki
    if 'AWS' in agents['agentName']  and 'IPv6' not in str(agents['agentName']):
        agent_id = agents['agentId']
        agent_name = agents['agentName']

        # creating dictionary that contains name w/ region and the agent ID
        aws_agent_dict = {'agent_name' : agent_name, 'agent_id' : agent_id}

        # appending aws_agent_dict to the aws_destination_agent_list
        aws_destination_agent_list.append(aws_agent_dict)

    # Filtering out IPv6 due to lack of support on Umbrella + Meraki
    elif 'Azure' in agents['agentName']  and 'IPv6' not in str(agents['agentName']):
        agent_id = agents['agentId']
        agent_name = agents['agentName']

        # creating dictionary that contains name w/ region and the agent ID
        azure_agent_dict = {'agent_name' : agent_name, 'agent_id' : agent_id}

        # appending azure_agent_dict to the azure_destination_agent_list
        azure_destination_agent_list.append(azure_agent_dict)

    # Filtering out IPv6 due to lack of support on Umbrella + Meraki
    elif 'GCP' in agents['agentName']  and 'IPv6' not in str(agents['agentName']):
        agent_id = agents['agentId']
        agent_name = agents['agentName']

        # creating dictionary that contains name w/ region and the agent ID
        gcp_agent_dict = {'agent_name' : agent_name, 'agent_id' : agent_id}

        # appending gcp_agent_dict to the gcp_destination_agent_list
        gcp_destination_agent_list.append(gcp_agent_dict)

    elif west_us_agent_name == agents['agentName']:
        west_us_agent_id = agents['agentId']

    elif east_us_agent_name == agents['agentName']:
        east_us_agent_id = agents['agentId']

destination_list_of_dictionaries = aws_destination_agent_list + azure_destination_agent_list + \
     gcp_destination_agent_list

print(len(destination_list_of_dictionaries))

for test in destination_list_of_dictionaries:

    # crafting testnames for east and west tests
    west_us_test_name = 'MMO: West US Agent (gduraj-raw) testing to: ' + str(test['agent_name'])
    east_us_test_name = 'MMO: East US Agent (HotelA-PC2) testing to: ' + str(test['agent_name'])

    # crafting body for HTTP Post to create test in TE dashboard for East US Agent
    create_east_us_test_data = { "interval": 300,
        "agents": [
          {"agentId": east_us_agent_id} 
        ],
        "testName": east_us_test_name,
        "targetAgentId": test['agent_id'],
        "port": 49153,
        "alertsEnabled": 0,
      }

    #print(create_east_us_test_data)

    # crafting body for HTTP Post to create test in TE dashboard for West US Agent
    create_west_us_test_data = { "interval": 300,
        "agents": [
          {"agentId": west_us_agent_id} 
        ],
        "testName": west_us_test_name,
        "targetAgentId": test['agent_id'],
        "port": 49153,
        "alertsEnabled": 0,
      }

    #print(create_west_us_test_data)

    create_east_test = create_agent_to_agent_test(email=your_email, api_token=your_apikey, \
    payload=your_optional_payload, body = json.dumps(create_east_us_test_data)) 

    create_west_test = create_agent_to_agent_test(email=your_email, api_token=your_apikey, \
    payload=your_optional_payload, body = json.dumps(create_west_us_test_data)) 

    print(create_east_test)
    print(create_west_test)
