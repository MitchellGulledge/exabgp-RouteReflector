# exabgp-RouteReflector

This route reflector is used to steer branch traffic from SD WAN nodes to the best performing DC where a MX/vMX is being hosted. EXABGP is used to manipulate BGP advertisements based on test data probing hosted ThousandEyes cloud agents across all regions in GCP/Azure/AWS. 

Below is a Diagram that reflects high level the operational flow of the solution:

![Test Image 1](EXA-TE-topology.png)

