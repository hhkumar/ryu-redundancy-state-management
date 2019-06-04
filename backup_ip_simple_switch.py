#Backup controller application
#Modified simple_siwtch_13.py to add temporary IP based flows instead of permanent MAC based flows

import ast
import os.path
import requests
from netmiko import ConnectHandler
from netmiko import SCPConn
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ether_types

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.ip_to_port = {}
	
	#We are creating a netmiko connection to the backup ryu server.
        #This will be used to transfer the state configuration file
        #between servers so that same state is maintained across both
        #ryu controller applications in case one goes down and comes up
        #again.

        ryu_vm = {
            "device_type": "linux",
            "ip": "10.10.10.20",
            "username": "ryu",
            "password": "ryu",
            "secret": "ryu",
        }
        net_connect = ConnectHandler(**ryu_vm)
        net_connect.enable()
        self.scp_conn = SCPConn(net_connect)

	#Check if the state configuration file exists and takes the
        #information into variable so that the dictionary mapping does not
        #have to be learned again

        if os.path.exists("/home/ryu/state.conf"):
            print("State configuration file exists. Importing from /home/ryu/state.conf...")
            with open("/home/ryu/state.conf","r") as state_file:
                lines = state_file.readlines()
            if lines:
                self.ip_to_port = ast.literal_eval(lines[0][:-1])
                self.mac_to_port = ast.literal_eval(lines[1][:-1])
                print(self.ip_to_port)
                print(self.mac_to_port)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        if idle_timeout:
            if buffer_id:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, idle_timeout=idle_timeout,
                                    instructions=inst)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority, idle_timeout=idle_timeout,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)
        else:
            if buffer_id:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
	        
	#Check if the primary server is reachable using api, then ignore it
	#This signifies that the primary server is able to answer requests.
	#If the request times out, then the request is served by the backup server.

	try:
		switch_list_resp = requests.get("http://10.10.10.20:8080/stats/switches")
	except:
		print("Port not open to accept api requests in 10.10.10.20. Switching to Backup server!!!")
		
		if os.path.exists("/home/ryu/state.conf"):
                    print("State configuration file exists. Importing from /home/ryu/state.conf...")
            	    with open("/home/ryu/state.conf","r") as state_file:
                	lines = state_file.readlines()
            	    if lines:
                	self.ip_to_port = ast.literal_eval(lines[0][:-1])
                	self.mac_to_port = ast.literal_eval(lines[1][:-1])
                	print(self.ip_to_port)
                	print(self.mac_to_port)

		if ev.msg.msg_len < ev.msg.total_len:
		    self.logger.debug("packet truncated: only %s of %s bytes",
				      ev.msg.msg_len, ev.msg.total_len)
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		in_port = msg.match['in_port']

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]
		pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)

		if eth.ethertype == ether_types.ETH_TYPE_LLDP:
		    # ignore lldp packet
		    return
		dst = eth.dst
		src = eth.src

		dpid = datapath.id
		self.mac_to_port.setdefault(dpid, {})
		self.ip_to_port.setdefault(dpid,{})

		self.mac_to_port[dpid][src] = in_port

		if dst in self.mac_to_port[dpid]:
		    out_port = self.mac_to_port[dpid][dst]
		else:
		    out_port = ofproto.OFPP_FLOOD
		
		#Modification in order to add flows based on IP addresses instead
        	#of MAC addresses.

		if pkt_ipv4:
		    ip_src = pkt_ipv4.src
		    ip_dst = pkt_ipv4.dst

		    self.ip_to_port[dpid][ip_src] = in_port

		    #Prints current state
		    
		    print(self.ip_to_port)
		    print(self.mac_to_port)

		    #Write the current state (dictionary) to a file state.conf
            	    #and transfer the file to the backup server to maintain synchronization

		    with open("/home/ryu/state.conf","w+") as state_file:
			state_file.write(str(self.ip_to_port)+"\n")
			state_file.write(str(self.mac_to_port)+"\n")

		    self.scp_conn.scp_transfer_file("/home/ryu/state.conf","state.conf")

		    if ip_dst in self.ip_to_port[dpid]:
			out_port = self.ip_to_port[dpid][ip_dst]

		    actions = [parser.OFPActionOutput(out_port)]
		    
		    #Allowing flows to timeout after 5 seconds to account for topology changes

		    idle_timeout = 5

		    if out_port != ofproto.OFPP_FLOOD:
			    match = parser.OFPMatch(in_port=in_port, eth_type=2048 ,ipv4_dst=ip_dst, ipv4_src=ip_src)
			    # verify if we have a valid buffer_id, if yes avoid to send both
			    # flow_mod & packet_out
			    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
				self.add_flow(datapath, 1, match, actions, msg.buffer_id, idle_timeout)
				return
			    else:
				self.add_flow(datapath, 1, match, actions, idle_timeout)

		actions = [parser.OFPActionOutput(out_port)]

		data = None
		if msg.buffer_id == ofproto.OFP_NO_BUFFER:
		    data = msg.data

		out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
					  in_port=in_port, actions=actions, data=data)
		datapath.send_msg(out)
