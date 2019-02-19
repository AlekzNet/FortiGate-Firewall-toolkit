# FortiGate-Firewall-toolkit
A set of programs to download, upload, convert, analyze and create a policy for FortiGate firewalls


## Files


* fgt-get.sh - Shell script to remotely collect Fortigate configs
* fgt-get.exp - Expect script to remotely get and save the full configuration
* fgt.list - list of FGT firewall IP's and hostnames
* fgt-set.sh - Shell script to remotely configure Fortigate firewalls
* fgt-set.exp - Expect script to remotely configure Fortigate firewalls
* fgt-set.cmd - commands to be remotely executed on Fortigate firewalls
* [genacl.py](https://github.com/AlekzNet/FortiGate-Firewall-toolkit/blob/master/doc/genacl.md) - utility to generate Cisco ASA, FortiGate or CheckPoint policy from a proto-policy. See also https://github.com/AlekzNet/Cisco-ASA-ACL-toolkit

## Requirements

* Expect (for the data collector)
* Python 2.7
* Netaddr

Install netaddr:

```sh
pip install netaddr
```

## Data collecting

* Edit fgt.list and place a list of the firewall IP-addresses and firewall hostnames (as in the FGT config). No empty lines.
* Enter username/passwords in fgt-get.sh, or uncomment lines that take the info from the keyboard
* Run fgt-get.sh. It will: 
  * create directories with the firewall names
  * log onto the firewalls
  * run the following commands:
    * show full
  * save the result in the fwname.conf file in the fwname directories

