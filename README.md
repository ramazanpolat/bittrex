# Python 3 client for Bittrex REST API 
Python client for Bittrex REST API 

## Features

* **Completely annotated design**: You don't have to guess or remember parameters and return types. Your ide will auto complete almost everything.
* **Paper trading**: Includes `Papertrex` class which is compatible with original `Bittrex` class. Any buy or sell order is simulated with real market data. You don't have to lose money in order to test your strategy or learn API.
* **Rate limit mitigation**: Once you reach rate limit of Bittrex, API slows down to cooperate with Bittrex API, so your requests never get rejected because of rate limiting.  

## Example

```python
from bittrex import Bittrex

b = Bittrex(apikey='<YOUR_APIKEY>', secret='<YOUR_SECRET', understood='understood')

err, balances = b.get_balances_dict()
if not err:
    for coin, balance_info in balances.items():
        print(f'Coin:{coin} - {balance_info}')
```
Output:

```
Coin:BLK - {'Currency': 'BLK', 'Balance': 1e-08, 'Available': 1e-08, 'Pending': 0.0, 'CryptoAddress': None}
Coin:BTC - {'Currency': 'BTC', 'Balance': 0.70257111, 'Available': 0.70257111, 'Pending': 0.0, 'CryptoAddress': '1M8gBWB33onbgfiXMuZrugUuNfycbG8dgr'}
Coin:ZEN - {'Currency': 'ZEN', 'Balance': 0.00958101, 'Available': 0.00958101, 'Pending': 0.0, 'CryptoAddress': None}
```

All other methods works the same.

Methods return a a tuple in a format of `tuple[error, result]`.

If `error` is `None` then there is no error and you use the `result`, otherwise `error` contains the error message.

Typical calling convention I used is something like this:

```
err, result = b.method(params)
if err:
    print('Error:', err)
else:
    # use result
    print(result)
```

## Paper trading

Using real market and real coin is risky. You may lose your valuable coins. You can use `Papertrex` to avoid this.

All buy and sell requests act like they are really sending request to Bittrex but in reality, it is just a simulation.

Papertrex fetches real-time price and candle information from market.  

Normally, when you issue a **real** buy or a sell order, your order gets placed first. 

Then depending on highest bid price or lowest ask price, your order might be in 3 states: `fulfilled`, `partially fulfilled` or `pending`.

**Papertrex** simulates this with a background job. Just like a real order, your order will be in any of these states.

This will help you to get familiar with API and develop buy/sell strategies.    
