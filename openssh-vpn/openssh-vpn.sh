#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
SSH_SOCKET=$(mktemp -u -p "$SCRIPT_DIR")

if [ "$USER" != "root" ]; then
  echo "ERROR: this script must be run as the root user." 1>&2
  exit -1
fi

function error_exit {
  echo "ERROR: $1" >&2
  
  if [ $2 -gt -1 ]; then
    control_c
  fi
  
  exit $2
}

function server_cmd {
  ssh -X -S "$SSH_SOCKET" root@"$SERVER" "$1"
}

function ssh_client_command {
  ssh -S "$SSH_SOCKET" -O $* "$SERVER"
}

function control_c {
  echo ""
  server_cmd "iptables -t nat -F"
  echo "INFO: Flushed the NAT firewall table on the server"
  echo -n "INFO: Terminating the SSH connection..."
  ssh -S "$SSH_SOCKET" -O exit "$SERVER"
  exit 0
}

function process_args {
  options=':s:n:m:k'
  
  while getopts "$options" option; do
    case "$option" in
      s ) SERVER="$OPTARG" && [ -n "$PRIV_KEY" ] || PRIV_KEY="$SCRIPT_DIR/$SERVER.privkey" ;;
      n ) NETWORK="$OPTARG" ;;
      m ) NETMASK="$OPTARG" ;;
      k ) PRIV_KEY="$OPTARG" ;;
      \? ) echo "Unknown option: -$OPTARG" 1>&2; exit -2 ;;
      :  ) echo "Missing option argument for -$OPTARG" 1>&2; exit -3 ;;
      *  ) echo "Unimplimented option: -$OPTARG" 1>&2; exit -4 ;;
    esac
  done
  
  #shift $(($OPTIND - 1))
  
  [ -n "$SERVER"  ] || error_exit "You must specifiy a server with the -s argument." -5
  [ -n "$NETWORK" ] || error_exit "You must specifiy a network with the -n argument." -6
  [ -n "$NETMASK" ] || error_exit "You must specifiy a netmask with the -m argument." -7
}

process_args $*

# trap the SIGINT signal (most often a "ctrl+c" keystroke) and cleanup before exiting
trap control_c SIGINT

ssh -NTf -M -S "$SSH_SOCKET" -o ServerAliveInterval=120 -w 0:0 -D 7777 -i "$PRIV_KEY" root@"$SERVER"
[ $? -eq 0 ] || error_exit "could not connect to the SSH server '$SERVER'" -1
echo "INFO: SSH connection established (control socket at '$SSH_SOCKET')"

server_cmd "echo 1 > /proc/sys/net/ipv4/ip_forward"
[ $? -eq 0 ] || error_exit "could not enable IP forwarding on '$SERVER'" 1
echo "INFO: Turned on IP forwarding on the server"

server_cmd "ifconfig tun0 10.0.0.100 pointopoint 10.0.0.200"
[ $? -eq 0 ] || error_exit "could not initialize the tunnel interface on '$SERVER'" 2
echo "INFO: Initialized the point-to-point tunnel interface on the server"

server_iface=$(server_cmd "route -n | grep $NETWORK" | awk '{ print $8 }')
server_cmd "iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o $server_iface -j MASQUERADE"
[ $? -eq 0 ] || error_exit "could not enable IP masquerading on '$SERVER'" 3
echo "INFO: Added an IP masquerading firewall rule on the server"

ifconfig tun0 10.0.0.200 pointopoint 10.0.0.100
[ $? -eq 0 ] || error_exit "could not initialize tunnel interface on local system" 4
echo "INFO: Initialized the point-to-point tunnel interface on the client"

route add -net "$NETWORK" netmask "$NETMASK" gw 10.0.0.100
[ $? -eq 0 ] || error_exit "could not add network route on local system" 5
echo "INFO: Added a route for the VPN network on the client"

echo -n "INFO: VPN connected.  Press <CTRL> + C to disconnect..."

# wait for user input and process any keystrokes appropriately
while [ /bin/true ]; do
  read -n 1 char
  
  case "$char" in
    c )
      char=""
      echo -e "\nINFO: Detected 'c' key press.  Spawning remote terminal session to '$SERVER'..."
      server_cmd
      echo -n "INFO: VPN still connected.  Press <CTRL> + C to disconnect..."
      ;;
    s )
      echo ""
      ;;
  esac
  
  sleep 1s
done
