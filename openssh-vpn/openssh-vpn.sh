#!/bin/bash

if [ "$USER" != "root" ]; then
  echo "ERROR: this script must be run as the root user." >&2
  exit -1
fi

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
ENABLE_SOCKS_PROXY=0
SOCKS_PROXY_PORT=7777
ENABLE_KEEPALIVE=1
KEEPALIVE_INTERVAL=120
ENABLE_RDP_FORWARDING=0
RDP_LOCAL_PORT="13389"
RDP_REMOTE_HOST="localhost"
RDP_REMOTE_PORT="3389"
TMP_DIR="$SCRIPT_DIR"

if [ -r /etc/openssh-vpn.cfg ]; then
  echo "INFO: Reading system-wide configuration..."
  source /etc/openssh-vpn.cfg
fi

if [ -r ~/.openssh-vpn ]; then
  echo "INFO: Reading user configuration..."
  source ~/.openssh-vpn
elif [ "$SUDO_USER" != "" ]; then
  if [ -r "/home/$SUDO_USER/.openssh-vpn" ]; then
    echo "INFO: Reading sudo-user configuration..."
    source /home/$SUDO_USER/.openssh-vpn
  fi
fi

SSH_SOCKET=$(mktemp -u -p "$TMP_DIR")
SSH_ARG_LIST="-NTf -M -y -S "$SSH_SOCKET" -w any:any"

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
  SRV_TUN_COUNT=$(server_cmd "ifconfig -a | grep -Eo '^tun[0-9]+' | sort -n | wc -l")
  
  if [ $SRV_TUN_COUNT -le 1 ]; then
    #server_cmd "iptables -t nat -F"
    #echo "INFO: Flushed the NAT firewall table on the server"
    server_cmd "iptables -t nat -D POSTROUTING -s 169.254.0.0/16 -o ${SERVER_IFACE} -j MASQUERADE"
    echo "INFO: Removed IP masquerading firewall rule on the server"
  fi
  
  echo -n "INFO: Terminating the SSH connection..."
  ssh -S "$SSH_SOCKET" -O exit "$SERVER"
  exit 0
}

function process_script_args {
  options=':s:n:m:k'
  
  while getopts "$options" option; do
    case "$option" in
      s ) SERVER="$OPTARG" ;;
      n ) NETWORK="$OPTARG" ;;
      m ) NETMASK="$OPTARG" ;;
      k ) PRIV_KEY="$OPTARG" ;;
      \? ) echo "Unknown option: -${OPTARG}" 1>&2; exit -2 ;;
      :  ) echo "Missing option argument for -${OPTARG}" 1>&2; exit -3 ;;
      *  ) echo "Unimplimented option: -${OPTARG}" 1>&2; exit -4 ;;
    esac
  done
  
  [ -n "$SERVER"  ] || error_exit "You must specifiy a server with the -s argument." -5
  [ -n "$NETWORK" ] || error_exit "You must specifiy a network with the -n argument." -6
  [ -n "$NETMASK" ] || error_exit "You must specifiy a netmask with the -m argument." -7
}

function build_ssh_arg_list {
  if [ $ENABLE_SOCKS_PROXY -ne 0 ]; then
    SSH_ARG_LIST="$SSH_ARG_LIST -D $SOCKS_PROXY_PORT"
  fi

  if [ $ENABLE_KEEPALIVE -ne 0 ]; then
    SSH_ARG_LIST="$SSH_ARG_LIST -o ServerAliveInterval=$KEEPALIVE_INTERVAL"
  fi

  if [ $ENABLE_RDP_FORWARDING -ne 0 ]; then
    SSH_ARG_LIST="$SSH_ARG_LIST -L${RDP_LOCAL_PORT}:${RDP_REMOTE_HOST}:${RDP_REMOTE_PORT}"
  fi

  if [ "$PRIV_KEY" != "" ]; then
    SSH_ARG_LIST="$SSH_ARG_LIST -i $PRIV_KEY"
  fi
}

process_script_args $*
build_ssh_arg_list

# trap the SIGINT signal (most often a "ctrl+c" keystroke) and cleanup before exiting
trap control_c SIGINT

# Establish the primary SSH connection
ssh $SSH_ARG_LIST root@"$SERVER"
[ $? -eq 0 ] || error_exit "could not connect to the SSH server '${SERVER}'" -1
echo "INFO: SSH connection established (control socket at '${SSH_SOCKET}')"

LOCAL_TUN_DEV=$(ifconfig -a | grep -Eo '^tun[0-9]+' | sort -n | tail -1)
REMOTE_TUN_DEV=$(server_cmd "ifconfig -a | grep -Eo '^tun[0-9]+' | sort -n | tail -1")
echo "INFO: Local tunneling device is ${LOCAL_TUN_DEV}"
echo "INFO: Remote tunneling device is ${REMOTE_TUN_DEV}"

server_cmd "echo 1 > /proc/sys/net/ipv4/ip_forward"
[ $? -eq 0 ] || error_exit "could not enable IP forwarding on '${SERVER}'" 1
echo "INFO: Turned on IP forwarding on the server"

LOCAL_TUN_IP="169.254.1"$(echo "$REMOTE_TUN_DEV" | sed 's/^tun//')".10"$(echo "$LOCAL_TUN_DEV" | sed 's/^tun//')
REMOTE_TUN_IP="169.254."$(echo "$REMOTE_TUN_DEV" | sed 's/^tun//')".10"$(echo "$REMOTE_TUN_DEV" | sed 's/^tun//')
#REMOTE_TUN_IP="169.254.${REMOTE_TUN_DEV}.10${REMOTE_TUN_DEV}"

server_cmd "ifconfig ${REMOTE_TUN_DEV} ${REMOTE_TUN_IP} pointopoint ${LOCAL_TUN_IP}"
[ $? -eq 0 ] || error_exit "could not initialize the tunnel interface on '${SERVER}'" 2
echo "INFO: Initialized the point-to-point tunnel interface on the server"

SERVER_IFACE=$(server_cmd "route -n | grep ${NETWORK}" | awk '{ print $8 }')
server_cmd "iptables -t nat -A POSTROUTING -s 169.254.0.0/16 -o ${SERVER_IFACE} -j MASQUERADE"
[ $? -eq 0 ] || error_exit "could not enable IP masquerading on '${SERVER}'" 3
echo "INFO: Added an IP masquerading firewall rule on the server"

ifconfig "$LOCAL_TUN_DEV" "$LOCAL_TUN_IP" pointopoint "$REMOTE_TUN_IP"
[ $? -eq 0 ] || error_exit "could not initialize tunnel interface on local system" 4
echo "INFO: Initialized the point-to-point tunnel interface on the client"

route add -net "$NETWORK" netmask "$NETMASK" gw "$REMOTE_TUN_IP"

[ $? -eq 0 ] || error_exit "could not add network route on local system" 5
echo "INFO: Added a route for the VPN network on the client"

echo -n "INFO: VPN connected.  Press <CTRL> + C to disconnect..."

# wait for user input and process any keystrokes appropriately
while [ /bin/true ]; do
  read -n 1 char
  
  case "$char" in
    c )
      char=""
      echo -e "\nINFO: Detected 'c' key press.  Spawning remote terminal session to '${SERVER}'..."
      server_cmd
      echo -n "INFO: VPN still connected.  Press <CTRL> + C to disconnect..."
      ;;
    s )
      echo ""
      ;;
  esac
  
  sleep 1s
done
