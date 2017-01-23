from stockanalyser.stock import Stock
from stockanalyser.analysis.levermann import (Levermann, prev_weekday,
                                              closest_weekday, prev_month)
from stockanalyser.mymoney import Money
import pytest
import datetime

def test_eval_analyst_rating():
    s = Stock("VOW.DE")
    l = Levermann(s)

    # no rating set/rating not available
    assert l.eval_analyst_rating() == 0

    s.analyst_recommendation_rating = 1
    assert l.eval_analyst_rating() == -1

    s.analyst_recommendation_rating = 2
    assert l.eval_analyst_rating() == 0

    s.analyst_recommendation_rating = 5
    assert l.eval_analyst_rating() == 1

def test_eval_quarterly_figures_reaction():
    s = Stock("VOW.DE")
    l = Levermann(s)

    d = datetime.date(2015, 2, 5)
    s.last_quarterly_figures_date = d
    l.eval_quarterly_figures_reaction()

def test_prev_weekday():
    assert prev_weekday(datetime.date(2017, 1, 16)) == datetime.date(2017,1, 13)
    assert prev_weekday(datetime.date(2017, 1, 13)) == datetime.date(2017,1, 12)
    assert prev_weekday(datetime.date(2017, 1, 10)) == datetime.date(2017,1, 9)

def test_closest_weekday():
    assert closest_weekday(datetime.date(2017, 1, 16)) == datetime.date(2017,1,16)
    assert closest_weekday(datetime.date(2017, 1, 15)) == datetime.date(2017,1,16)
    assert closest_weekday(datetime.date(2017, 1, 14)) == datetime.date(2017,1,13)
    assert prev_weekday(datetime.date(2017, 1, 13)) == datetime.date(2017,1, 12)
    assert prev_weekday(datetime.date(2017, 1, 10)) == datetime.date(2017,1, 9)


def test_prev_month():
    p = prev_month(datetime.date(2017, 1, 1))
    assert p.year == 2016 and p.month == 12
    p = prev_month(datetime.date(2017, 3, 10))
    assert p.year == 2017 and p.month == 2


def test_quote_chg():
    s = Stock("VOW.DE")
    l = Levermann(s)
    l.eval_quote_chg_6month()
    l.eval_quote_chg_1year()

def test_3month_reversal():
    s = Stock("VOW.DE")
    l = Levermann(s)
    l.eval_three_month_reversal()

def test_earning_growth():
    s = Stock("VOW.DE")
    s.set_eps(datetime.date.today().year + 1, Money(1, "EUR"))
    s.set_eps(datetime.date.today().year, Money(5, "EUR"))
    l = Levermann(s)
    l.eval_earning_growth()
