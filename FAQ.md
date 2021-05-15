# Frequently Asked Question

## 

## Errors and solutions


| Error   |   Solution |
|----------|-------------|
| `APIError(code=-1021): Timestamp for this request was 1000ms ahead of the server's time` |  Update your computer/servers ntp server to `time.nist.gov` |
|`'NoneType' object has no attribute 'encode'`| Your API key is not correct. Ensure the environment (mainnet/testnet) matches the API keys used |
|`Insufficient Funds` Error| Make sure you have the available USDT. Make sure you dont have lots of it on order. Ensure you QUANTITY is at least 15. |
| Other Binance API Errors| Go take a look at the [Binance API documentation Exceptions](https://github.com/binance/binance-spot-api-docs/blob/master/errors.md) page |

## Questions and Answers

| Question   |   Answer |
|----------|-------------|
|Why am I getting weird / unreliable values using testnet|  Testnet isn't for testing strategies. It's for testing functionality. We've talked about adding functionality to the main script to run against mainnet but with bogus buys. nothing yet. |
| What type of funds are required for this to work in PROD |  Ensure you account has the following: <ul><li>BNB ~$5 USD (used for fees / transactions)</li><li>Atleast X USDT matching your QUANTITYxMAX_COINS  (>$15 USD but check config for 'QUANTITY')</li></ul> |
|Why am I getting weird / unreliable values using testnet|  Testnet isn't for testing strategies. It's for testing functionality. We've talked about adding functionality to the main script to run against mainnet but with bogus buys. nothing yet. |



