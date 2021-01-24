# encoding: utf-8
import sys, datetime, json, re

from workflow.workflow import ICON_NETWORK
from workflow import Workflow3, ICON_ERROR, ICON_CLOCK
from workflow.web import post
from decimal import Decimal

"""Request Model
{
    "method": "spotRateHistory",
    "data": {
        "base": "JPY", // from
        "term": "USD", // to
        "period": "week"
    }
}
"""

"""Response Model
{
    "data": {
        "CurrentInterbankRate": 0.0097,
        "HistoricalPoints":[...]
        "fetchTime": 1611425616625
    }
}
"""

NUMBER = re.compile(r"^\-?\d+(\.\d*)?$")


def main(wf):
    if len(wf.args) == 0:
        return

    arg = wf.args[0]
    stream = RealStringIO(arg)
    try:
        balance, _from, to = parse_input(stream)
        cache_key = _from + "_" + to
        exchange_rate, last_fetch_time = (0, "")
        cached = wf.cached_data(
            cache_key, max_age=28800  # seconds, 8 hours to be expired
        )

        if cached is None:
            payload = json.dumps(
                {
                    "method": "spotRateHistory",
                    "data": {"base": _from, "term": to, "period": "day"},
                }
            )
            exchange_rate, last_fetch_time = get_exchange_rate(payload)
            wf.cache_data(cache_key, (exchange_rate, last_fetch_time))
        else:
            exchange_rate, last_fetch_time = cached

        result = Decimal(balance) * Decimal(exchange_rate)
        print_val = "{0:f}".format(result.normalize())

        wf.add_item(
            title=print_val,
            subtitle="Fetch time: %s" % (last_fetch_time),
            copytext=print_val,
        )
    except WaitingForInputError as we:
        wf.add_item(title="Waiting for more input", subtitle=str(we), icon=ICON_CLOCK)
    except NetworkError as ne:
        wf.add_item(title="Network Error", subtitle=str(ne), icon=ICON_NETWORK)
    except ParseError:
        pass
    except Exception as pe:
        wf.add_item(title="Error", subtitle=str(pe), icon=ICON_ERROR)

    wf.send_feedback()


def get_exchange_rate(payload):
    r = post(
        "https://adsynth-ofx-quotewidget-prod.herokuapp.com/api/1",
        data=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,  # seconds
    )
    if r.status_code < 400:
        data = r.json()

        try:
            data["error"]
            raise Exception(data["error"])
        except KeyError:
            pass

        exchange_rate = str(data["data"]["CurrentInterbankRate"])
        fetch_time = datetime.datetime.fromtimestamp(
            data["data"]["fetchTime"] // 1000
        ).strftime("%Y-%m-%d %H:%M:%S")
        return exchange_rate, fetch_time
    else:
        raise NetworkError(r.status_code)


class ParseError(Exception):
    pass


class WaitingForInputError(Exception):
    pass


class NetworkError(Exception):
    pass


class RealStringIO:
    def __init__(self, initial_value=""):
        self._value = initial_value
        self._len = len(initial_value)
        self._cursor = 0

    def read(self):
        if self._cursor >= self._len:
            return ""
        c = self._value[self._cursor]
        self._cursor += 1
        return c

    def readable(self):
        return self._cursor < self._len


def parse_input(stream):
    if not stream.readable():
        raise WaitingForInputError("no balance specified")
    balance = parse_balance(stream)

    if not stream.readable():
        raise WaitingForInputError("no source currency code specified")
    _from = parse_from(stream)

    if not stream.readable():
        raise WaitingForInputError("expecting to/To/in/In")
    parse_prep(stream)

    if not stream.readable():
        raise WaitingForInputError("no target currency code specified")
    to = parse_to(stream)
    return (balance, _from.upper(), to.upper())


def parse_balance(stream):
    c = " "
    while stream.readable() and c == " ":
        c = stream.read()

    v = c
    while stream.readable():
        c = stream.read()
        if c == " ":
            break
        v += c
    if NUMBER.match(v) is None:
        raise ParseError("expect number, but got: ", v)
    if Decimal(v).is_signed():
        raise ParseError("balance should be positive number")
    return v


def parse_from(stream):
    c = " "
    while stream.readable() and c == " ":
        c = stream.read()

    v = c
    while stream.readable():
        c = stream.read()
        if c == " ":
            break
        v += c

    if not v.isalpha() or len(v) != 3:
        raise ParseError("expect currency code, but got: " + v)
    return v


def parse_prep(stream):
    c = " "
    while stream.readable() and c == " ":
        c = stream.read()

    v = c
    while stream.readable():
        c = stream.read()
        if c == " ":
            break
        v += c
    if v.upper() != "TO" and v.upper() != "IN":
        raise ParseError("expect to/in")


def parse_to(stream):
    c = " "
    while stream.readable() and c == " ":
        c = stream.read()

    v = c
    while stream.readable():
        c = stream.read()
        if c == " ":
            break
        v += c

    if not v.isalpha() or len(v) != 3:
        raise ParseError("expect currency code, but got: " + v)
    return v


if __name__ == "__main__":
    wf = Workflow3()
    sys.exit(wf.run(main))