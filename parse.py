import re

from decimal import Decimal

NUMBER = re.compile(r"^\-?\d+(\.\d*)?$")


class ParseError(Exception):
    pass


class WaitingForInputError(Exception):
    pass


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