from bittrex import Bittrex


b = Bittrex(apikey='<YOUR_APIKEY>', secret='<YOUR_SECRET', understood='understood')

err, balances = b.get_balances_dict()
if not err:
    for coin, balance_info in balances.items():
        print(f'Coin:{coin} - {balance_info}')
