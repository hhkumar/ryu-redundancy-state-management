A proof of concept that demonstrates redundancy and state management in Ryu controllers running on two servers. Ryu in itself does not support clustering or any redundancy mechanism in order to manage failover scenarios. The aim of this project is to work around the existing libraries of Ryu (ofctl_rest.py) to provide redundancy among multiple controllers in an active-passive mode. Also, network state is made available to the passive controller to facilitate efficient failover.

# Getting Started

Requirements:

- [Ryu](https://osrg.github.io/ryu/) controller installed on primary and standy servers
- Open vSwitch (OVS) configured to connect to the ryu controllers
- Hosts for simulating workstations

The entire environment can be set up on physical devices or in GNS3 as shown below.

# Environment setup

![GNS3 environment](https://user-images.githubusercontent.com/47063895/58900425-618b3f00-86bc-11e9-9af5-c9f69e743819.PNG)

The above environment is set up in GNS3. There are two Ubuntu 16.04.6 LTS VMs which will be used as primary and backup controllers (named as RyuVM-1 and RyuVMBackup-1 respectively). A simple SDN network is simulated using three OVS's which will connect to both controllers using the ManagementSW. A bunch of workstations are connected to the OVS to simulate hosts in the network.

# Working

Primary controller is initiated using the command:
```
ryu run ip_simple_switch_13.py ofctl_rest.py
```
Backup controller is initiated using the command:
```
ryu run backup_ip_simple_switch.py ofctl_rest.py
```

When both controllers are initiated and OVS is connected to both, packet ins are sent to both contollers. To prevent simultaneous addition of flow entries, we have designated a primary and backup controller. 

## No failover scenario - No previous state information

As requests are sent to both controllers, the backup checks whether the primary is active using ofctl_rest API calls. If the request goes through, the backup controller does not take any action. The primary controller switches based on IP addresses, creates the file "state.conf" and copies it to the backup controller for state management.

Primary controller accepting packet ins and rest calls:
![1](https://user-images.githubusercontent.com/47063895/58905889-07907680-86c8-11e9-9266-4f7abf5836ee.PNG)
Backup controller on standby:
![2](https://user-images.githubusercontent.com/47063895/58905896-0d865780-86c8-11e9-9057-8fc5680a0119.PNG)
state.conf file sent to backup controller
![3](https://user-images.githubusercontent.com/47063895/58906051-54744d00-86c8-11e9-9ae9-a23131bf0f9a.PNG)

## Failover scenario - Existing previous state information

The backup controller fails to get API response when the primary controller is down. In that case, it loads the current state.conf file and routes packets seamlessly.

Primary controller taken down:
![1](https://user-images.githubusercontent.com/47063895/58906887-37407e00-86ca-11e9-8b92-6c767a00c738.PNG)
Backup controller kicking in with previous state information sent by primary:
![2](https://user-images.githubusercontent.com/47063895/58906901-3c053200-86ca-11e9-960f-93fc48fcc13b.PNG)
State configuration file updated in primary continuously. Below image shows addition of host 192.168.1.3 to the state file:
![3](https://user-images.githubusercontent.com/47063895/58906920-4293a980-86ca-11e9-9ae1-05057d9a351d.PNG)

## Failover scenario - Primary coming back online

Once the primary controller comes back online, it loads the existing state.conf file (sent by backup controller) and takes on requests. The backup controller once again goes on standby.

Primary controller back online. Loads state.conf automatically:
![1](https://user-images.githubusercontent.com/47063895/58908324-80460180-86cd-11e9-9638-0ee4d9bd0cc6.PNG)
Serving packet ins:
![2](https://user-images.githubusercontent.com/47063895/58908332-8340f200-86cd-11e9-8946-3213a8da5eb0.PNG)
