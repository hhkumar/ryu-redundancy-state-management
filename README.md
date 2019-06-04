A proof of concept that demonstrates redundancy and state management in Ryu controllers running on two servers. Ryu in itself does not support clustering or any redundancy mechanism in order to manage failover scenarios. The aim of this project is to work around the existing libraries of Ryu (ofctl_rest.py) to provide redundancy among multiple controllers in an active-passive mode. Also, network state is made available to the passive controller to facilitate efficient failover.

# Environment setup

![GNS3 environment](https://user-images.githubusercontent.com/47063895/58900425-618b3f00-86bc-11e9-9af5-c9f69e743819.PNG)

The above environment is set up in GNS3. There are two Ubuntu 16.04.6 LTS VMs which will be used as primary and backup controllers (named as RyuVM-1 and RyuVMBackup-1 respectively). A simple SDN network is simulated using three OVS's which will connect to both controllers using the ManagementSW. A bunch of workstations are connected to the OVS to simulate hosts in the network.

