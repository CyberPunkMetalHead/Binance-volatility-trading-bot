#!/bin/bash

APP_ROOT="/app"
CREDS_FILE=${APP_ROOT}/creds.yml
CONFIG_FILE=${APP_ROOT}/config.yml

cat << EOF > $CREDS_FILE
prod:
  access_key: $PROD_ACCESS_KEY
  secret_key: $PROD_SECRET_KEY
test:
  access_key: $TEST_ACCESS_KEY
  secret_key: $TEST_SECRET_KEY
EOF

# script options
[[ -n $TEST_MODE ]]  && sed -i "s/\(  TEST_MODE: \).*$/\1${TEST_MODE}/" $CONFIG_FILE
[[ -n $LOG_TRADES ]] && sed -i "s/\(  LOG_TRADES: \).*$/\1${LOG_TRADES}/" $CONFIG_FILE
[[ -n $LOG_FILE ]]   && sed -i "s~\(  LOG_FILE: \).*$~\1${LOG_FILE}~" $CONFIG_FILE      # $LOG_FILE could contain a slash, so use different delimiter
[[ -n $BINANCE_US ]] && sed -i "s/\(  BINANCE_US: \).*$/\1${BINANCE_US}/" $CONFIG_FILE

# trading options
[[ -n $CHANGE_IN_PRICE ]]  && sed -i "s/\(  CHANGE_IN_PRICE: \).*$/\1${CHANGE_IN_PRICE}/" $CONFIG_FILE
[[ -n $MAX_COINS ]]        && sed -i "s/\(  MAX_COINS: \).*$/\1${MAX_COINS}/" $CONFIG_FILE
[[ -n $PAIR_WITH ]]        && sed -i "s/\(  PAIR_WITH: \).*$/\1${PAIR_WITH}/" $CONFIG_FILE
[[ -n $QUANTITY ]]         && sed -i "s/\(  QUANTITY: \).*$/\1${QUANTITY}/" $CONFIG_FILE
[[ -n $STOP_LOSS ]]        && sed -i "s/\(  STOP_LOSS: \).*$/\1${STOP_LOSS}/" $CONFIG_FILE
[[ -n $TIME_DIFFERENCE ]]  && sed -i "s/\(  TIME_DIFFERENCE: \).*$/\1${TIME_DIFFERENCE}/" $CONFIG_FILE
[[ -n $TAKE_PROFIT ]]      && sed -i "s/\(  TAKE_PROFIT: \).*$/\1${TAKE_PROFIT}/" $CONFIG_FILE

echo "end prep"
