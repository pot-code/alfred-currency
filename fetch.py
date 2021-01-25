import sys, datetime, json

from workflow.web import post
from workflow import Workflow3


class NetworkError(Exception):
    pass


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


if __name__ == "__main__":
    wf = Workflow3()
    args = sys.argv
    _from, to = args[1], args[2]
    cache_key = _from + "_" + to
    payload = json.dumps(
        {
            "method": "spotRateHistory",
            "data": {"base": _from, "term": to, "period": "day"},
        }
    )

    try:
        exchange_rate, last_fetch_time = get_exchange_rate(payload)
        wf.cache_data(cache_key, (exchange_rate, last_fetch_time))
    except NetworkError as ne:
        wf.cache_data("network_error", ne)
    except Exception as e:
        wf.cache_data("error", str(e))
