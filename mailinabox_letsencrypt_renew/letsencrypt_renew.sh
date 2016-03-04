#!/bin/bash

# Renew Let's Encrypt SSL for MailInABox Server
# Created by: Jared Sutton <jpsutton@gmail.com>

# Config vars
DOMAIN="mycool.domain"
LE_CFG="/etc/letsencrypt/cli.ini"
LE_LOG="/var/log/letsencrypt/letsencrypt.log"
LE_PATH="/root/letsencrypt"
CERT_PATH="/home/user-data/ssl"
ALERT_EMAIL_ADDR="mycoolemail@mycool.domain"
MIN_RENEW_DAYS=14

# Move into the folder with the cert
cd "${CERT_PATH}"

# Calculate days until expiration
EXPIRE_TS=$(openssl x509 -enddate -noout -in ssl_certificate.pem | awk -F'=' '{ print $2 }')
EXPIRE_UNIX=$(date --date="${EXPIRE_TS}" "+%s")
NOW_UNIX=$(date "+%s")
EXPIRE_DAYS=$(( $(( ${EXPIRE_UNIX} - ${NOW_UNIX} )) / 86400 ))

# Renew the cert if it will expire within MIN_RENEW_DAYS days of expiration
if [ ${EXPIRE_DAYS} -lt ${MIN_RENEW_DAYS} ]; then
  "${LE_PATH}/letsencrypt-auto" --config "${LE_CFG}" -d "${DOMAIN}" certonly

  if [ $? -ne 0 ]; then
    # Notify the admins of any errors
    ERRORLOG=$(tail "${LE_LOG}")
    echo -e "RENEWAL ERROR: ${DOMAIN} certificate will expire in ${EXPIRE_DAYS} days! \n \nError data:\n" $ERRORLOG | mail -s "Lets Encrypt Cert Alert" ${ALERT_EMAIL_ADDR}
  else
    # link the new cert into the mailinabox config
    ln -sf /etc/letsencrypt/live/${DOMAIN}/fullchain*.pem ssl_certificate.pem
    ln -sf "/etc/letsencrypt/csr/$(ls -tr /etc/letsencrypt/csr/ | tail -1)" ssl_cert_sign_req.csr
    ln -sf /etc/letsencrypt/live/${DOMAIN}/privkey*.pem ssl_private_key.pem

    # restart the webserver
    /etc/init.d/nginx restart

    # notify the admins
    echo -e "${DOMAIN} certificate has been renewed! \n \n" $ERRORLOG | mail -s "Lets Encrypt Cert Renewed" ${ALERT_EMAIL_ADDR}
  fi
else
  echo "Certificate for ${DOMAIN} will expire in ${EXPIRE_DAYS} days; not renewing just yet."
fi

exit 0
