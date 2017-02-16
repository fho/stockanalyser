from enum import Enum, unique
from stockanalyser.mymoney import Money
import time
from datetime import datetime
from stockanalyser.exceptions import InvalidValueError


@unique
class QueryType(Enum):
    PERCENT = 1
    CURRENCY = 2
    DATE = 3
    YAHOO_ANALYST_RATING = 4
    STOCK_SYMBOL = 5
    URL = 6


def query_input(value_name, val_type):
    while True:
        try:
            if val_type == QueryType.PERCENT:
                v = input("> Please enter %s: " % value_name)
                v = float(v)
                validate_percent_value(v)
                return v
            elif val_type == QueryType.CURRENCY:
                v = input("> Please enter %s (Format:"
                          " VALUE 3-LETTER-CURRENCY-SYMBOL): " % value_name)
                v = v.split()
                if len(v) != 2:
                    raise InvalidValueError("expected Format: VALUE"
                                            " 3-LETTER-CURRENCY-SYMBOL")
                m = Money(float(v[0]), v[1].upper())
                return m
            elif val_type == QueryType.DATE:
                v = input("> Please enter %s (Format: DD.MM.YYYY): " %
                          value_name)
                return validate_str_date(v)
            elif val_type == QueryType.YAHOO_ANALYST_RATING:
                v = float(input("> Please enter %s: " % value_name))
                if v >= 1 and v <= 5:
                    return v
            elif val_type == QueryType.STOCK_SYMBOL:
                v = input("> Please enter %s: " % value_name)
                return v
            elif val_type == QueryType.URL:
                v = input("> Please enter %s: " % value_name)
                return v

        except (ValueError, InvalidValueError) as e:
            print("Error: %s" % e)
            print("Please enter a valid %s value" % val_type)


def validate_str_date(v):
    struct = time.strptime(v, "%d.%m.%Y")
    d = datetime.fromtimestamp(time.mktime(struct)).date()
    return d

def validate_percent_value(v):
    if v > 100:
        raise InvalidValueError("Invalid percent value '%s': must be >=0,"
                                " <=100" % v)
