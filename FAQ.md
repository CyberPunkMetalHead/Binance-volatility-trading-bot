# Frequently Asked Question

## Questions
Question: I'm running in [testnet](https://testnet.binance.vision/) and my values / and data doesnt seem correct?
Answer: Testnet should ONLY be used to test functionality. It does not mimic the market. If things seem off here it's because it is. 

## Errors and solutions


| Error   |   Solution |
|----------|-------------|
| `APIError(code=-1021): Timestamp for this request was 1000ms ahead of the server's time` |  Update your computer/servers ntp server to `time.nist.gov` |
|`'NoneType' object has no attribute 'encode'`| Your API key is not correct. Ensure the environment (mainnet/testnet) matches the API keys used |