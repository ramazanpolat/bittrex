from typing import Any, List, Tuple, Optional
import traceback
from urllib.parse import urlencode
import time
import hmac
import hashlib
import requests
from prodict import Prodict
from datetime import datetime


# region ENUMS
class BittrexFillType:
    FILL = "FILL"
    PARTIAL_FILL = "PARTIAL_FILL"


class BittrexOrderType:
    BUY = "BUY"
    SELL = "SELL"


class BittrexOpenOrderType:
    LIMIT_BUY = "LIMIT_BUY"
    LIMIT_SELL = "LIMIT_SELL"


class BittrexTickIntervalTypes:
    D1 = 'day'
    H1 = 'hour'
    M30 = 'thirtymin'
    M5 = 'fivemin'
    M1 = 'onemin'

    @classmethod
    def all_types(cls):
        return dict(D1=cls.D1,
                    H1=cls.H1,
                    M30=cls.M30,
                    M5=cls.M5,
                    M1=cls.M1
                    )


# endregion

# region RESPONSES

class BittrexAPIResponse(Prodict):
    message: str
    success: bool
    result: dict

    @property
    def has_error(self):
        return not self.success

    @property
    def error_msg(self):
        return self.message


class BittrexCurrency(Prodict):
    Currency: str
    CurrencyLong: str
    MinConfirmation: int
    TxFee: float
    IsActive: bool
    CoinType: str
    BaseAddress: str
    Notice: str


class BittrexMarket(Prodict):
    MarketCurrency: str
    BaseCurrency: str
    MarketCurrencyLong: str
    BaseCurrencyLong: str
    MinTradeSize: float
    MarketName: str
    IsActive: bool
    Created: str
    Notice: str
    IsSponsored: str
    LogoUrl: str


class BittrexMarketSummary(Prodict):
    MarketName: str
    High: float
    Low: float
    Volume: float
    Last: float
    BaseVolume: float
    TimeStamp: str
    Bid: float
    Ask: float
    OpenBuyOrders: int
    OpenSellOrders: int
    PrevDay: float
    Created: str


class BittrexQuantityRate(Prodict):
    Quantity: float
    Rate: float


class BittrexOrderBook(Prodict):
    buy: List[BittrexQuantityRate]
    sell: List[BittrexQuantityRate]


class BittrexTicker(Prodict):
    Bid: float
    Ask: float
    Last: float

    @property
    def spread(self) -> float:
        return self.Ask - self.Bid

    @property
    def spread_percent(self) -> float:
        return 100 * self.spread / self.Last


class BittrexBuyLimit(Prodict):
    uuid: str


class BittrexSellLimit(Prodict):
    uuid: str


class BittrexWithdraw(Prodict):
    uuid: str


class BittrexMarketHistory(Prodict):
    Id: int
    TimeStamp: str
    Quantity: float
    Price: float
    Total: float
    FillType: str
    OrderType: str


class BittrexOpenOrder(Prodict):
    Uuid: str
    OrderUuid: str
    Exchange: str
    OrderType: BittrexOpenOrderType
    Quantity: float
    QuantityRemaining: float
    Limit: float
    CommissionPaid: float
    Price: float
    PricePerUnit: float
    Opened: str
    Closed: str
    CancelInitiated: bool
    ImmediateOrCancel: bool
    IsConditional: bool
    Condition: str
    ConditionTarget: str


class BittrexOrder(Prodict):
    AccountId: Any
    OrderUuid: str
    Exchange: str
    Type: BittrexOpenOrderType
    Quantity: float
    QuantityRemaining: float
    Limit: float
    Reserved: float
    ReserveRemaining: float
    CommissionReserved: float
    CommissionReserveRemaining: float
    CommissionPaid: float
    Price: float
    PricePerUnit: float
    Opened: str
    Closed: str
    IsOpen: bool
    Sentinel: str
    CancelInitiated: bool
    ImmediateOrCancel: bool
    IsConditional: bool
    Condition: str
    ConditionTarget: str


class BittrexBalance(Prodict):
    Currency: str
    Balance: float
    Available: float
    Pending: float
    CryptoAddress: str
    Requested: bool
    Uuid: Any


class BittrexDepositAddress(Prodict):
    Currency: str
    Address: str


class BittrexOrderHistory(Prodict):
    OrderUuid: str
    Exchange: str
    TimeStamp: str
    OrderType: BittrexOpenOrderType
    Limit: float
    Quantity: float
    QuantityRemaining: float
    Commission: float
    Price: float
    PricePerUnit: float
    IsConditional: bool
    Condition: str
    ConditionTarget: str
    ImmediateOrCancel: bool


class BittrexWithdrawalDepositHistory(Prodict):
    PaymentUuid: str
    Currency: str
    Amount: float
    Address: str
    Opened: str
    Authorized: bool
    PendingPayment: bool
    TxCost: float
    TxId: Any
    Canceled: bool
    InvalidAddress: bool


class BittrexCandle(Prodict):
    O: float
    H: float
    L: float
    C: float
    V: float
    T: str
    BV: float


# endregion


class Bittrex:
    __shared_instance = None
    DATETIME_PARSE_FORMAT = "%Y-%m-%dT%H:%M:%S"

    # FILL_TYPES = BittrexFillType
    # ORDER_TYPES = BittrexOrderType
    # OPEN_ORDER_TYPES = BittrexOpenOrderType
    # TICK_INTERVAL_TYPES = BittrexTickIntervalTypes

    # Balance = BittrexBalance
    # BuyLimit = BittrexBuyLimit
    # Candle = BittrexCandle
    # Currency = BittrexCurrency
    # DepositAddress = BittrexDepositAddress
    # DepositHistory = BittrexWithdrawalDepositHistory
    # Market = BittrexMarket
    # MarketHistory = BittrexMarketHistory
    # MarketSummary = BittrexMarketSummary
    # OpenOrder = BittrexOpenOrder
    # Order = BittrexOrder
    # OrderBook = BittrexOrderBook
    # OrderHistory = BittrexOrderHistory
    # QuantityRate = BittrexQuantityRate
    # SellLimit = BittrexSellLimit
    # Ticker = BittrexTicker
    # Withdraw = BittrexWithdraw
    # WithdrawalHistory = BittrexWithdrawalDepositHistory

    def __init__(self, apikey: str, secret: str, rate_limit: int = 5, account_name: str = 'NOT_PRIVODED',
                 http_keep_alive: bool = False, understood=""):

        self.account_name = account_name
        # https://bittrex.com/Api/v2.0/pub/market/getticks?marketName=USDT-BTC&tickInterval=day
        # https://bittrex.com/api/v2.0/pub/market/getlatesttick?marketName=BTC-NEO&tickInterval=onemin
        self._api20 = ['getticks', 'getlatesttick']
        self._public = ['getmarkets', 'getcurrencies', 'getticker', 'getmarketsummaries', 'getmarketsummary',
                        'getorderbook', 'getmarkethistory']
        self._market = ['buylimit', 'buymarket', 'selllimit', 'sellmarket', 'cancel', 'getopenorders']
        self._account = ['getbalances', 'getbalance', 'getdepositaddress', 'withdraw', 'getorder', 'getorderhistory',
                         'getwithdrawalhistory', 'getdeposithistory']

        self.http_keep_alive = http_keep_alive

        self.key = apikey
        self.rate_limit = rate_limit
        self.secret = secret
        self.last_call = None
        self.timeout = 15

        self.calls = []

        print('Bittrex API instance started for "{}".'.format(self.account_name))
        print('This is RISKY! You may lose money. Know what you are doing!')

        warn = False if understood == 'understood' else True

        while warn:
            answer = input('Type "quit" to exit or "understood" to continue:')
            if answer == 'understood':
                break
            elif answer == 'quit':
                exit(0)

        self.warmed = False
        if self.http_keep_alive:
            self.requests_session = requests.Session()
            self._warm_up()

        Bittrex.__shared_instance = self
        self.market_info = None
        err, market_info = self.get_markets_dict()
        if err:
            print(f"Error on bittrex_api.markets_dict:{err}")
        else:
            self.market_info = market_info

    def _query(self, method, values=None) -> Tuple[Any, Optional[BittrexAPIResponse]]:
        """
        Actual method for sending queries to Bittrex

        :param method: which method to call
        :param values: additional values depending on the method
        :return: error(if any), BittrexAPIResponse
        """
        if values is None:
            values = {}
        try:
            if method in self._public:
                url = 'https://bittrex.com/api/v1.1/public/'
            elif method in self._market:
                url = 'https://bittrex.com/api/v1.1/market/'
            elif method in self._account:
                url = 'https://bittrex.com/api/v1.1/account/'
            elif method in self._api20:
                url = 'https://bittrex.com/api/v2.0/pub/market/'
            #     https://bittrex.com/api/v2.0/pub/market/getticks?marketname=USDT-BTC&tickinterval=day
            else:
                return True, None

            url += method + '?' + urlencode(values)

            if method not in self._public and method not in self._api20:
                url += '&apikey=' + str(self.key)
                nonce = int(time.time())
                url += '&nonce=' + str(nonce)
                signature = hmac.new(self.secret.encode(),
                                     url.encode(),
                                     hashlib.sha512).hexdigest()
                headers = {'apisign': signature}
                # print('nonce=', nonce)
                # print('apisign=', signature)
                # print('headers:', headers)
                # print('url:', url)
                # exit(0)
            else:
                headers = {}

            self._wait_rate_limit()

            self.calls.append(datetime.utcnow().timestamp())
            if self.http_keep_alive:
                response = self.requests_session.get(url, headers=headers, timeout=self.timeout).json()
            else:
                response = requests.get(url, headers=headers, timeout=self.timeout).json()

            bittrexapi_response: BittrexAPIResponse = BittrexAPIResponse.from_dict(response)
            if bittrexapi_response.has_error:
                return bittrexapi_response.message, None
            return False, bittrexapi_response

        except Exception as exception1:
            print('Exception:{}'.format(exception1))
            print(traceback.format_exc())
            return exception1, None

    @classmethod
    def _parse_dt(cls, s: str) -> Optional[datetime]:
        """
        Parse a Bittrex date string and convert to a python datetime object
        :param s: Datetime string
        :return: datetime
        """
        if s is None:
            return None
        if "." in s:
            s = s.split(".")[0]
        return datetime.strptime(s, cls.DATETIME_PARSE_FORMAT)

    @classmethod
    def shared_instance(cls, apikey: str, secret: str, rate_limit: int = 5, account_name: str = 'NOT_PRIVODED',
                        http_keep_alive: bool = True, understood=""):
        """
        Creates a shared instance.

        :param apikey: Bittrex API key
        :param secret: API secret
        :param rate_limit: rate limit
        :param account_name: An account name if you work on multiple Bittrex account(for visibility only)
        :param http_keep_alive: Keep HTTP connection open, speeds up requests
        :param understood: You must understand that this is a risky business
        :return: BittrexAPI
        """
        local_params = locals()
        if not cls.has_shared_instance():
            print("BittrexAPI singleton instance not found, creating one")
            local_params.pop('cls', None)
            cls.__shared_instance = cls(**local_params)

        return cls.__shared_instance

    @classmethod
    def has_shared_instance(cls):
        return Bittrex.__shared_instance is not None

    @classmethod
    def _to_market(cls, coin: str, quote: str):
        """
        Convert from base currency, quote currency pair to market name

        e.g. BTC, USDT to (BTC-USDT).

        :param coin: str
        :param quote: str
        :return: str
        """
        return f"{quote.upper()}-{coin.upper()}"

    @classmethod
    def _from_market(cls, market: str):
        """
        Convert market name to base currency, quote currency.

        e.g. BTC-USDT to (BTC, USDT).

        :param market: BASE-QUOTE(BTC-USDT)
        :return: List[base_currency, quote_currency]
        """
        # basecoin, quote
        return market.split("-")

    def _warm_up(self):
        # Warming up for Connection=keep-alive...
        err, ticker = self.get_ticker('USDT-BTC')
        if err:
            self.warmed = False
        else:
            self.warmed = True

    def _calls_in_last_sec(self):
        now = datetime.utcnow().timestamp()
        calls_in_last_second = [call for call in self.calls if call >= (now - 1)]
        self.calls = calls_in_last_second
        return calls_in_last_second

    def _wait_rate_limit(self):
        """Wait for rate limit"""
        now = datetime.utcnow().timestamp()
        calls_in_last_sec2 = self._calls_in_last_sec()
        if len(calls_in_last_sec2) >= self.rate_limit:
            wait_time = (calls_in_last_sec2[0] - (now - 1))
            print(self.calls)
            print('Rate limit({} per second) reached! Waiting for {} second...'.format(self.rate_limit, wait_time))
            if wait_time > 0:
                time.sleep(wait_time)
            else:
                print('wait_time < 0')
            # Wait finished

    def get_candles(self, market_name: str, tick_interval: str) -> Tuple[Any, List[BittrexCandle]]:
        """
        Get candles

        :param market_name: BASE-QUOTE(BTC-USDT)
        :param tick_interval: TICK_INTERVAL_TYPES
        :return: error(if any), List[BittrexCandle]
        """
        if tick_interval not in list(BittrexTickIntervalTypes.all_types()):
            return f'tick_interval should be one of {list(BittrexTickIntervalTypes.all_types())}', []

        err, response = self._query('getticks', {'marketname': market_name, 'tickinterval': tick_interval})

        candle_list: List[BittrexCandle] = []
        for candle_dict in response.result:
            candle_list.append(BittrexCandle.from_dict(candle_dict))

        return err, candle_list

    def get_latest_candle(self, market_name, tick_interval) -> Tuple[Any, List[BittrexCandle]]:
        """
        Get latest candle

        :param market_name: BASE-QUOTE(BTC-USDT)
        :param tick_interval: TICK_INTERVAL_TYPES
        :return: error(if any), List[BittrexCandle]
        """
        if tick_interval not in list(BittrexTickIntervalTypes.all_types()):
            return f'tick_interval should be one of {list(BittrexTickIntervalTypes.all_types())}', []

        err, response = self._query('getlatesttick', {'marketname': market_name, 'tickinterval': tick_interval})

        candle_list: List[BittrexCandle] = []
        for candle_dict in response.result:
            candle_list.append(BittrexCandle.from_dict(candle_dict))

        return err, candle_list

    def get_markets(self) -> Tuple[Any, List[BittrexMarket]]:
        """
        Get markets

        :return: error(if any), List[BittrexMarket]
        """
        err, response = self._query('getmarkets')
        if err:
            return err, []

        return err, [BittrexMarket.from_dict(m) for m in response.result]

    def get_markets_dict(self) -> Tuple[Any, dict]:
        """
        Get markets as dict

        :return: error(if any), dict
        """
        err, markets = self.get_markets()
        if err:
            return err, {}

        return err, {m.MarketName: m for m in markets}

    def get_currencies(self) -> Tuple[Any, List[BittrexCurrency]]:
        """
        Get currencies

        :return: error(if any), List[BittrexCurrency]
        """
        err, response = self._query('getcurrencies')
        if err:
            return err, []
        return err, [BittrexCurrency.from_dict(m) for m in response.result]

    def get_ticker(self, market: str) -> Tuple[Any, Optional[BittrexTicker]]:
        """
        Get ticker.
        :param market: BASE-QUOTE(BTC-USDT)
        :return: error(if any), BittrexTicker
        """
        err, response = self._query('getticker', {'market': market})
        if err:
            return err, None

        ticker: BittrexTicker = BittrexTicker.from_dict(dict(response.result))

        return err, ticker

    def get_market_summaries(self) -> Tuple[Any, List[BittrexMarketSummary]]:
        """
        Get market summaries

        :return: error(if any), List[BittrexMarketSummary]
        """
        err, response = self._query('getmarketsummaries')
        if err:
            return err, []

        return err, [BittrexMarketSummary.from_dict(m) for m in response.result]

    def get_market_summaries_dict(self):
        """
        Get market summaries as dict

        :return: error(if any), dict
        """
        err, summaries = self.get_market_summaries()
        if err:
            return err, summaries

        sum_dict = {}

        for currency_info in summaries:
            market = currency_info['MarketName']
            sum_dict[market] = currency_info

        return err, sum_dict

    def panic_sell_all_for_btc(self):
        """
        Sells all in btc markets!

        :return:
        """
        err, balances_dict = self.get_balances_dict()
        if err:
            return err, balances_dict

        print('{} coins will be sold!'.format(len(balances_dict)))

        input('Press ENTER to continue.')

        for currency, balance_info in balances_dict.items():
            if balance_info['Available'] == 0:
                continue
            if currency == 'BTC':
                continue
            print('Panic selling {}...'.format(currency))
            market_name = 'BTC-{}'.format(currency)

            # input('Will be selling {} of {}! Press enter to continue.'.format(balance_info['Available'], currency))
            print('waiting for 1 second...')
            time.sleep(1)

            err, sell_order = self.sell_market(market_name, balance_info['Available'])
            print('Panic sell order placed for {}'.format(currency))
            if err:
                print('Error on panic_sell_for_btc for {}'.format(currency))
            else:
                print('Panic sell order for {} is successful.'.format(currency))

    def get_balances_dict(self) -> Tuple[Optional[Any], Optional[dict]]:
        err, balances = self.get_balances()
        if err:
            return err, None

        balances_dict = {}

        for currency_info in balances:
            currency_symbol = currency_info['Currency']
            if currency_info['Balance'] == 0:
                continue
            balances_dict[currency_symbol] = currency_info

        return err, balances_dict

    def get_estimated_values(self):
        err, balances_dict = self.get_balances_dict()
        if err:
            return err, balances_dict

        err, market_summaries_dict = self.get_market_summaries_dict()
        if err:
            return err, market_summaries_dict

        btc_market_summary = market_summaries_dict['USDT-BTC']
        btc_price_in_usdt = btc_market_summary['Ask']

        print('btc_price_in_usdt={} - btc_market_summary:{}'.format(btc_price_in_usdt, btc_market_summary))

        btc_balance = 0
        usdt_balance = 0
        altcoins_total_btc_worth = 0

        for currency, balance_info in balances_dict.items():
            currency_balance = balance_info['Balance']
            print('   {} Balance ={}'.format(currency, currency_balance))
            if currency_balance == 0:
                continue

            if currency == 'BTC':
                btc_balance = currency_balance
                continue

            if currency == 'USDT':
                usdt_balance = currency_balance
                continue

            btc_market_name = 'BTC-{}'.format(currency)
            market_summary_of_currency = market_summaries_dict.get(btc_market_name, None)

            if market_summary_of_currency is None:
                continue

            print('   {} Summary={}'.format(btc_market_name, market_summary_of_currency))

            altcoins_total_btc_worth += currency_balance * market_summary_of_currency['Ask']
            print('   altcoins_total_btc_worth ={}'.format(altcoins_total_btc_worth))

        estimated_total_btc = altcoins_total_btc_worth + btc_balance

        altcoins_total_usdt_worth = altcoins_total_btc_worth * btc_price_in_usdt

        estimated_total_usdt = estimated_total_btc * btc_price_in_usdt

        altcoins_count = len(balances_dict)

        btc_worth_per_coin = altcoins_total_btc_worth / altcoins_count if altcoins_count > 0 else 0

        # usdt_percent = round(100 * usdt_balance / estimated_total_usdt, 3)
        # btc_percent = round(100 * btc_balance / estimated_total_btc, 3)
        # altcoins_percent = round(100 * altcoins_total_btc_worth / estimated_total_btc, 3)

        return False, {
            'btc_balance': btc_balance,
            'usdt_balance': usdt_balance,
            'estimated_total_btc': estimated_total_btc,
            'estimated_total_usdt': estimated_total_usdt,
            'altcoins_total_btc_worth': altcoins_total_btc_worth,
            'altcoins_total_usdt_worth': altcoins_total_usdt_worth,
            'altcoins_count': altcoins_count,
            'btc_worth_per_coin': btc_worth_per_coin
        }

    def get_market_summary(self, market: str) -> Tuple[Any, List[BittrexMarketSummary]]:
        """
        Get market summary

        :param market: BASE-QUOTE(BTC-USDT)
        :return: error(if any), List[BittrexMarketSummary]
        """
        err, response = self._query('getmarketsummary', {'market': market})
        if err:
            return err, []

        return err, [BittrexMarketSummary.from_dict(r) for r in response.result]

    def get_orderbook(self, market, order_type='both') -> Tuple[Any, Optional[BittrexOrderBook]]:
        """
        Get order book

        :param market: BASE-QUOTE(BTC-USDT)
        :param order_type: 'buy', 'sell' or 'both'
        :return: error(if any), BittrexOrderBook
        """
        err, orderbook = self._query('getorderbook', {'market': market, 'type': order_type})
        if err:
            return err, None

        return err, BittrexOrderBook.from_dict(orderbook.result)

    def get_market_history(self, market) -> Tuple[Any, List[BittrexMarketHistory]]:
        """
        Get market history

        :param market: BASE-QUOTE(BTC-USDT)
        :return: error(if any), List[BittrexMarketHistory]
        """
        err, market_history_list = self._query('getmarkethistory', {'market': market})
        if err:
            return err, []

        return err, [BittrexMarketHistory.from_dict(mh) for mh in market_history_list]

    def buy_limit(self, market, quantity, buy_price) -> Tuple[Any, Optional[BittrexBuyLimit]]:
        """
        Limit buy

        :param market: BASE-QUOTE(BTC-USDT)
        :param quantity: amount to buy
        :param buy_price: buy from this price
        :return: error(if any), BittrexBuyLimit
        """
        print(f'REAL LIMIT BUY=Market:{market} Quantity:{quantity:.8f} Rate:{buy_price:.8f}')
        err, response = self._query('buylimit', {'market': market, 'quantity': quantity, 'rate': buy_price})
        if err:
            return err, None
        return err, BittrexBuyLimit.from_dict(response.result)

    def buy_market(self, market, quantity) -> Tuple[Any, BittrexBuyLimit]:
        """
        Buy from market price

        :param market: BASE-QUOTE(BTC-USDT)
        :param quantity: amount to buy
        :return: error(if any), BittrexBuyLimit
        """
        err, ticker = self.get_ticker(market)
        if err:
            print('Error on getting ask price:{}'.format(err))
            return err, BittrexBuyLimit()
        print('Ask price ={:.8f}'.format(ticker.Ask))
        return self.buy_limit(market, quantity, ticker.Ask)

    def sell_limit(self, market, quantity, sell_price) -> Tuple[Any, Optional[BittrexSellLimit]]:
        """
        Limit sell

        :param market: BASE-QUOTE(BTC-USDT)
        :param quantity: amount to sell
        :param sell_price: sell from this price
        :return: error(if any), BittrexSellLimit
        """
        print(f'REAL LIMIT SELL=Market:{market} Quantity:{quantity:.8f} Rate:{sell_price:.8f}')
        err, response = self._query('selllimit', {'market': market, 'quantity': quantity, 'rate': sell_price})
        if err:
            return err, None
        return err, BittrexSellLimit.from_dict(response.result)

    def sell_market(self, market, quantity) -> Tuple[Any, Optional[BittrexSellLimit]]:
        """
        Sell from market price.

        :param market: BASE-QUOTE(BTC-USDT)
        :param quantity: amount to sell
        :return: error(if any), BittrexSellLimit
        """
        err, ticker = self.get_ticker(market)
        if err:
            print(f'sell_market:Error on getting bid price:{err}')
            return err, None
        print(f'sell_market:Bid price ={ticker.Bid:.8f}')
        return self.sell_limit(market, quantity, ticker.Bid)

    def cancel(self, order_uuid) -> Tuple[Any, bool]:
        """
        Cancel an order by uuid

        :param order_uuid: str
        :return: error(if any), success(bool)
        """
        err, response = self._query('cancel', {'uuid': order_uuid})
        if err:
            print(f'cancel error for order {order_uuid}:{err}')
            return err, False
        return err, response.success

    def get_open_orders(self, market=None) -> Tuple[Any, List[BittrexOpenOrder]]:
        """
        Get open orders

        :param market: BASE-QUOTE(BTC-USDT)
        :return: error(if any), List[BittrexOpenOrder]
        """
        if market:
            err, response = self._query('getopenorders', {'market': market})
        else:
            err, response = self._query('getopenorders')

        if err:
            return err, []
        return err, [BittrexOpenOrder.from_dict(oo) for oo in response.result]

    def get_balances(self) -> Tuple[Any, List[BittrexBalance]]:
        """
        Get balances

        :return: error(if any), List[BittrexBalance]
        """
        err, response = self._query('getbalances')
        if err:
            return err, []
        return err, [BittrexBalance.from_dict(b) for b in response.result]

    def get_balance(self, currency) -> Tuple[Any, Optional[BittrexBalance]]:
        """
        Get balance

        :param currency: str
        :return: error(if any), List[BittrexBalance]
        """
        err, response = self._query('getbalance', {'currency': currency})
        if err:
            return err, None
        return err, BittrexBalance.from_dict(response.result)

    def get_deposit_address(self, currency) -> Tuple[Any, Optional[BittrexDepositAddress]]:
        """
        Get deposit address

        :param currency: str
        :return: error(if any), List[BittrexDepositAddress]
        """

        err, response = self._query('getdepositaddress', {'currency': currency})
        if err:
            return err, None
        return err, BittrexDepositAddress.from_dict(response.result)

    def withdraw(self, currency, quantity, address, paymentid=None) -> Tuple[Any, Optional[BittrexWithdraw]]:
        """
        Withdraw

        :param currency: a string literal for the currency (ie. BTC)
        :param quantity: amount of coins to withdraw
        :param address: the address where to send the funds
        :param paymentid: used for CryptoNotes/BitShareX/Nxt/XRP and any other coin that has a
         memo/message/tag/paymentid option
        :return: error(if any), List[BittrexWithdraw]
        """
        params = {'currency': currency, 'quantity': quantity, 'address': address}
        if paymentid:
            params['paymentid'] = paymentid
        err, response = self._query('withdraw', params)
        if err:
            return err, None
        return err, BittrexWithdraw.from_dict(response.result)

    def get_order(self, order_uuid) -> Tuple[Any, Optional[BittrexOrder]]:
        """
        Get an order

        :param order_uuid: str
        :return: error(if any), BittrexOrder
        """
        err, response = self._query('getorder', {'uuid': order_uuid})
        if err:
            return err, None
        return err, BittrexOrder.from_dict(response.result)

    def get_order_history(self, market=None) -> Tuple[Any, List[BittrexOrderHistory]]:
        """
        Get order history

        :param market: BASE-QUOTE(BTC-USDT)
        :return: error(if any), List[BittrexOrderHistory]
        """
        if market:
            err, response = self._query('getorderhistory', {'market': market})
        else:
            err, response = self._query('getorderhistory')

        if err:
            return err, []
        return err, [BittrexOrderHistory.from_dict(e) for e in response.result]

        # original code
        # return self.query('getorderhistory', {'market': market, 'count': count})

    def get_withdrawal_history(self, currency) -> Tuple[Any, List[BittrexWithdrawalDepositHistory]]:
        """
        Get withdrawal history

        :param currency: str
        :return: error(if any), List[BittrexWithdrawalDepositHistory]
        """
        if currency:
            err, response = self._query('getwithdrawalhistory', {'currency': currency})
        else:
            err, response = self._query('getwithdrawalhistory')

        if err:
            return err, []
        return err, [BittrexWithdrawalDepositHistory.from_dict(e) for e in response.result]

    def get_deposit_history(self, currency) -> Tuple[Any, List[BittrexWithdrawalDepositHistory]]:
        """
        Get deposit history

        :param currency: a string literal for the currency (ie. BTC)
        :return: error(if any), List[BittrexWithdrawalDepositHistory]
        """
        if currency:
            err, response = self._query('getdeposithistory', {'currency': currency})
        else:
            err, response = self._query('getdeposithistory')

        if err:
            return err, []
        return err, [BittrexWithdrawalDepositHistory.from_dict(e) for e in response.result]
