import threading
import time
import random
import uuid
from datetime import datetime
from typing import Tuple, Any, Optional, List

from bittrex import Bittrex, BittrexBuyLimit, BittrexSellLimit, BittrexOpenOrder, BittrexOrder, \
    BittrexBalance, BittrexOpenOrderType
from prodict import Prodict


def gen_id():
    str(uuid.uuid4())


def now():
    return datetime.utcnow()


class CompleteOrder(Prodict):
    Uuid: str  # oo
    OrderUuid: str
    Exchange: str
    OrderType: BittrexOpenOrderType  # oo
    Quantity: float
    QuantityRemaining: float
    Limit: float
    CommissionPaid: float
    Price: float
    PricePerUnit: float
    Opened: str
    CancelInitiated: bool
    ImmediateOrCancel: bool
    IsConditional: bool
    Condition: str
    ConditionTarget: str
    AccountId: Any  # order
    Type: BittrexOpenOrderType  # order
    Reserved: float  # order
    ReserveRemaining: float  # order
    CommissionReserved: float  # order
    CommissionReserveRemaining: float  # order
    Closed: str  # order
    IsOpen: bool  # order
    Sentinel: str  # order

    @property
    def display(self):
        return f"{self.OrderType}\t{self.Exchange}\t" \
            f"Qty:{self.Quantity}\tRemQty:{self.QuantityRemaining}\tClosed:{self.Closed}"


class Papertrex(Bittrex):
    """
    Class to make almost real operations on paper. No real buy or sell limit is issued. But keeps tracks of actions.
    Simulates buy or sell order.
    """

    @classmethod
    def _create_buy_order(cls, market, quantity, buy_price):
        pass

    @classmethod
    def _to_open_order(cls, co: CompleteOrder) -> BittrexOpenOrder:
        oo = BittrexOpenOrder()
        oo.Uuid: str = co.Uuid
        oo.OrderUuid: str = co.OrderUuid
        oo.Exchange: str = co.Exchange
        oo.OrderType: BittrexOpenOrderType = co.OrderType
        oo.Quantity: float = co.Quantity
        oo.QuantityRemaining: float = co.QuantityRemaining
        oo.Limit: float = co.Limit
        oo.CommissionPaid: float = co.CommissionPaid
        oo.Price: float = co.Price
        oo.PricePerUnit: float = co.PricePerUnit
        oo.Opened: str = co.Opened
        oo.Closed: str = co.Closed
        oo.CancelInitiated: bool = co.CancelInitiated
        oo.ImmediateOrCancel: bool = co.ImmediateOrCancel
        oo.IsConditional: bool = co.IsConditional
        oo.Condition: str = co.Condition
        oo.ConditionTarget: str = co.ConditionTarget

        return oo

    @classmethod
    def _to_order(cls, co: CompleteOrder) -> BittrexOrder:
        bo = BittrexOrder()
        bo.OrderUuid: str = co.OrderUuid
        bo.Exchange: str = co.Exchange
        bo.Quantity: float = co.Quantity
        bo.QuantityRemaining: float = co.QuantityRemaining
        bo.Limit: float = co.Limit
        bo.CommissionPaid: float = co.CommissionPaid
        bo.Price: float = co.Price
        bo.PricePerUnit: float = co.PricePerUnit
        bo.Opened: str = co.Opened
        bo.CancelInitiated: bool = co.CancelInitiated
        bo.ImmediateOrCancel: bool = co.ImmediateOrCancel
        bo.IsConditional: bool = co.IsConditional
        bo.Condition: str = co.Condition
        bo.ConditionTarget: str = co.ConditionTarget
        bo.AccountId: Any = co.AccountId
        bo.Type: BittrexOpenOrderType = co.Type
        bo.Reserved: float = co.Reserved
        bo.ReserveRemaining: float = co.ReserveRemaining
        bo.CommissionReserved: float = co.CommissionReserved
        bo.CommissionReserveRemaining: float = co.CommissionReserveRemaining
        bo.Closed: str = co.Closed
        bo.IsOpen: bool = co.IsOpen
        bo.Sentinel: str = co.Sentinel

        return bo

    def __init__(self, apikey: str, secret: str, rate_limit: int = 5, account_name: str = 'NOT_PRIVODED',
                 http_keep_alive: bool = False, understood=""):
        super().__init__(apikey, secret, rate_limit, account_name, http_keep_alive, understood)
        self._orders: List[CompleteOrder] = []
        self._spawn_order_issue_agent()

    def _spawn_order_issue_agent(self):
        t = threading.Thread(target=self._order_issue_agent, daemon=True)
        t.start()

    def _fulfill_order(self, order: CompleteOrder):
        order.Closed = now().strftime(self.DATETIME_PARSE_FORMAT)
        order.CancelInitiated = False
        order.QuantityRemaining = 0
        order.PricePerUnit = order.Limit
        order.Price = order.Quantity * order.Limit

    def _partly_fill_order(self, order: CompleteOrder):
        amount = random.uniform(0.0001, order.QuantityRemaining)
        amount = min(amount, order.Quantity)
        order.QuantityRemaining = amount
        order.PricePerUnit = order.Limit
        order.Price = (order.Quantity - order.QuantityRemaining) * order.Limit

    def _what_to_do_with_order(self, o: CompleteOrder, age):
        if o.OrderType == BittrexOpenOrderType.LIMIT_BUY or o.Type == BittrexOpenOrderType.LIMIT_BUY:
            if age < 60:
                if random.randint(1, 100) <= 100:
                    return "fulfill"

                if random.randint(1, 100) < 50:
                    return "partly_fill"

                return "nothing"
            elif age < 120:
                if random.randint(1, 100) < 50:
                    return "fulfill"

                if random.randint(1, 100) < 50:
                    return "partly_fill"

                return "nothing"
            elif age < 180:
                if random.randint(1, 100) < 100:
                    return "fulfill"

                if random.randint(1, 100) < 15:
                    return "partly_fill"

                return "nothing"

            return "nothing"
        else:
            if age < 60:
                if random.randint(1, 100) <= 100:
                    return "fulfill"

                if random.randint(1, 100) < 5:
                    return "partly_fill"

                return "nothing"
            elif age < 120:
                if random.randint(1, 100) < 5:
                    return "fulfill"

                if random.randint(1, 100) < 5:
                    return "partly_fill"

                return "nothing"
            elif age < 180:
                if random.randint(1, 100) < 5:
                    return "fulfill"

                if random.randint(1, 100) < 5:
                    return "partly_fill"

                return "nothing"

            return "nothing"

    def _order_issue_agent(self):
        while True:
            time.sleep(20)
            open_orders = [o for o in self._orders if o.Closed is None]
            for o in open_orders:
                age = now().timestamp() - self._parse_dt(o.Opened).timestamp()
                what_to_do = self._what_to_do_with_order(o, age)
                if what_to_do == 'nothing':
                    """---=== Doing nothing to order"""
                    continue
                if what_to_do == 'fulfill':
                    """---=== Fulfilling order"""
                    self._fulfill_order(o)
                    continue
                if what_to_do == 'partly_fill':
                    """---=== Partly filling order"""
                    self._partly_fill_order(o)
                    continue

    def buy_limit(self, market, quantity, buy_price) -> Tuple[Any, Optional[BittrexBuyLimit]]:
        """Paper buy_limit {market}: {quantity:.8f} x {buy_price:.8f}={quantity * buy_price:.8f} BTC"""
        response: BittrexBuyLimit = BittrexBuyLimit(uuid=gen_id())
        co = CompleteOrder()
        co.Uuid: str = response.uuid
        co.OrderUuid: str = co.Uuid
        co.Exchange: str = market
        co.OrderType: BittrexOpenOrderType = BittrexOpenOrderType.LIMIT_BUY
        co.Quantity: float = quantity
        co.QuantityRemaining: float = quantity
        co.Limit: float = buy_price
        co.CommissionPaid: float = 0
        co.Price: float = buy_price
        co.PricePerUnit: Optional[float] = None
        co.Opened: str = now().strftime(self.DATETIME_PARSE_FORMAT)
        co.CancelInitiated: bool = False
        co.ImmediateOrCancel: bool = False
        co.IsConditional: bool = False
        co.Condition: Optional[str] = None
        co.ConditionTarget: Optional[str] = None
        co.AccountId: Any = None
        co.Type: BittrexOpenOrderType = BittrexOpenOrderType.LIMIT_BUY
        co.Reserved: float = 0
        co.ReserveRemaining: float = 0
        co.CommissionReserved: float = 0
        co.CommissionReserveRemaining: float = 0
        co.Closed: Optional[str] = None
        co.IsOpen: bool = True
        co.Sentinel: str = "sentinel"

        self._orders.append(co)
        return False, response

    def sell_limit(self, market, quantity, sell_price) -> Tuple[Any, Optional[BittrexSellLimit]]:
        """Paper sell_limit {market}: {quantity:.8f} x {sell_price:.8f}={quantity * sell_price:.8f} BTC"""
        response: BittrexSellLimit = BittrexSellLimit(uuid=gen_id())
        self._create_buy_order(market, quantity, sell_price)
        co = CompleteOrder()
        co.Uuid: str = response.uuid
        co.OrderUuid: str = co.Uuid
        co.Exchange: str = market
        co.OrderType: BittrexOpenOrderType = BittrexOpenOrderType.LIMIT_SELL
        co.Quantity: float = quantity
        co.QuantityRemaining: float = quantity
        co.Limit: float = sell_price
        co.CommissionPaid: float = 0
        co.Price: float = sell_price
        co.PricePerUnit: Optional[float] = None
        co.Opened: str = now().strftime(self.DATETIME_PARSE_FORMAT)
        co.CancelInitiated: bool = False
        co.ImmediateOrCancel: bool = False
        co.IsConditional: bool = False
        co.Condition: Optional[str] = None
        co.ConditionTarget: Optional[str] = None
        co.AccountId: Any = None
        co.Type: BittrexOpenOrderType = BittrexOpenOrderType.LIMIT_SELL
        co.Reserved: float = 0
        co.ReserveRemaining: float = 0
        co.CommissionReserved: float = 0
        co.CommissionReserveRemaining: float = 0
        co.Closed: Optional[str] = None
        co.IsOpen: bool = True
        co.Sentinel: str = "sentinel"

        self._orders.append(co)
        return False, response

    def cancel(self, order_uuid) -> Tuple[Any, bool]:
        order = None
        for o in self._orders:
            if o.Uuid == order_uuid:
                order = o
                break
        if order:
            if order.Closed:
                return "Order already closed", False
            order.Closed = now().strftime(self.DATETIME_PARSE_FORMAT)
            order.CancelInitiated = True
            order.IsOpen = False
            order.PricePerUnit = order.Limit
            order.Price = order.PricePerUnit * order.Quantity
            """Canceled order: + order.display"""
            return False, True
        """Order not found to cancel: + order_uuid"""
        return "Order not found to cancel", False

    def get_open_orders(self, market=None) -> Tuple[Any, List[BittrexOpenOrder]]:
        result: List[BittrexOpenOrder] = [self._to_open_order(order) for order in self._orders if order.Closed is None]

        # for order in self._orders:
        #     if order.Closed is None:
        #         result.append(self._to_open_order(order))
        # if market is None:
        #     result.append(self.to_open_order(order))
        # elif order.Exchange == market:
        #     result.append(self.to_open_order(order))

        return False, result

    def get_order(self, order_uuid) -> Tuple[Any, Optional[BittrexOrder]]:
        result: Optional[BittrexOrder] = None
        for order in self._orders:
            if order.Uuid == order_uuid:
                result = self._to_order(order)
                break

        if result is None:
            return "Order not found", None
        return False, result

    def get_balance(self, currency) -> Tuple[Any, Optional[BittrexBalance]]:
        pass

    def get_balances(self) -> Tuple[Any, List[BittrexBalance]]:
        pass
