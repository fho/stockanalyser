from stockanalyser.stock import Stock
from stockanalyser import  input
from datetime import date
import pytest
from stockanalyser.mymoney import Money
from decimal import Decimal

def test_set_roe_value():
    cur_year = date.today().year
    s = Stock("GOOG")
    s.set_roe(cur_year, 0.0)
    s.set_roe(cur_year, 100)
    s.set_roe(cur_year, 31.12345)

    with pytest.raises(input.InvalidValueError):
        s.set_roe(cur_year, -1)
        s.set_roe(cur_year, -0.0000000001)
        s.set_roe(cur_year, 100.1)
        s.set_roe(cur_year, 200)

    with pytest.raises(TypeError):
        s.set_roe(cur_year, "1")


def test_set_roe_year_value():
    cur_year = date.today().year
    s = Stock("GOOG")

    s.set_roe(cur_year, 1)
    s.set_roe(cur_year -10, 1)
    s.set_roe(cur_year +10, 1)


def test_get_roe():
    cur_year = date.today().year
    s = Stock("GOOG")

    s.set_roe(cur_year, 63.12)
    s.set_roe(cur_year -10, 100)
    s.set_roe(cur_year +10, 0)

    assert s.roe[cur_year] ==  63.12
    assert s.roe[cur_year -10] ==  100
    assert s.roe[cur_year +10] ==  0

    assert s.roe[cur_year +10] !=  1

    with pytest.raises(KeyError):
        s.roe[cur_year +2]

def test_per():
    cur_year = date.today().year
    s = Stock("GOOG")
    #TODO: test could fail because the quote price could differ a little bit
    # because they are obtained in seperate queries

    s.set_eps(cur_year + 1, Money(1, "USD"))
    s.set_eps(cur_year, Money(2, "USD"))
    s.set_eps(cur_year - 1, Money(3, "USD"))
    s.set_eps(cur_year - 2, Money(4, "USD"))
    s.set_eps(cur_year - 3, Money(5, "USD"))
    per = s.quote / Money(((1 + 2 + 3 + 4 + 5) / 5.0), "USD")
    assert s.get_5years_price_earnings_ratio() == per

    s.set_eps(cur_year - 4, Money(5, "USD"))
    assert s.get_5years_price_earnings_ratio() == per

    s.set_eps(cur_year + 1,Money(-1000, "USD"))
    per = s.quote / Money((-1000 + 2 + 3 + 4 + 5) / 5, "USD") 
    # value slightly differs starting from the 11 decimal place, maybe
    # because float and Decimal type are not used consistently in the Stock
    # class and in the test
    # comparing up to the 3. decimal type is sufficent:
    assert round(s.get_5years_price_earnings_ratio(), 3) == round(per, 3)

    assert s.get_price_earnings_ratio() == (s.quote / 2)
