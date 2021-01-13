# exabgp Route Reflector

This route reflector is used to steer branch traffic from SD WAN nodes to the best performing DC where a MX/vMX is being hosted. EXABGP is used to manipulate BGP advertisements based on test data probing hosted ThousandEyes cloud agents across all regions in GCP/Azure/AWS. 

Below is a Diagram that reflects high level the operational flow of the solution:

![Test Image 1](EXA-TE-topology.png)

In the above solution both PoPs have their own NAT Gateways out to the internet. In the below examples we utilize Cisco Meraki vMXs deployed from the AWS Marketplace along with an ubuntu VM running the Docker Container.

# Pre-Requisites

The NAT Gateways at each PoP have routes pointing to branch subnets with their local vMX/MX local IP as the next hop. 

Default routes either generated from exabgp with the next hop as the local NAT Gateway. (This can be done on the Cisco Meraki MX/vMX in concentrator mode by adding 0.0.0.0/0 as a local subnet. In addition we can rely on exabgp to generate the default route and set the local gateway as the next hop. (This option would have to be added to the routes.py file as it does not exist today)
