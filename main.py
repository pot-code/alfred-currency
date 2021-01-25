# encoding: utf-8
import sys

from workflow import Workflow3, ICON_ERROR, ICON_CLOCK, ICON_NETWORK, ICON_SYNC
from workflow.background import run_in_background, is_running
from decimal import Decimal

from fetch import NetworkError
from parse import ParseError, WaitingForInputError, parse_input

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
            run_in_background(
                "fetch",
                ["/usr/bin/python", wf.workflowfile("fetch.py"), _from, to],
            )

        if is_running("fetch"):
            wf.rerun = 0.5
            wf.add_item(title="Fetching...", icon=ICON_SYNC)
        else:
            cached = wf.cached_data(
                cache_key, max_age=0
            )  # now can safely pull the data from cache
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


if __name__ == "__main__":
    wf = Workflow3()
    sys.exit(wf.run(main))