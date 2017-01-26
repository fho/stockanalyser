import logging
import calendar
import pickle
from datetime import date, timedelta
from stockanalyser.data_source import yahoo
from stockanalyser.exceptions import NotSupportedError, InvalidValueError
from stockanalyser.config import *
from stockanalyser import fileutils

logger = logging.getLogger(__name__)

THIS_YEAR = date.today().year
LAST_YEAR = date.today().year - 1


def is_weekday(adate):
    if adate.weekday() in (5, 6):
        return False

    return True


def prev_weekday(adate):
        _offsets = (3, 1, 1, 1, 1, 1, 2)
        return adate - timedelta(days=_offsets[adate.weekday()])


def closest_weekday(adate):
    if adate.weekday() == 6:
        return adate + timedelta(days=1)
    elif adate.weekday() == 5:
        return adate - timedelta(days=1)
    return adate


def last_weekday_of_month(adate):
    last_day = calendar.monthrange(adate.year, adate.month)[1]
    d = date(adate.year, adate.month, last_day)

    if not is_weekday(d):
        return prev_weekday(d)
    return d


def prev_month(adate):
    return date(adate.year, adate.month, 1) - timedelta(days=1)


class CriteriaRating(object):
    def __init__(self, value, points):
        self.value = value
        self.points = points


def levermann_pickle_path(symbol, dir=DATA_PATH):
        filename = fileutils.to_pickle_filename(symbol + ".levermann")
        path = os.path.join(dir, filename)
        return path


def unpickle_levermann(symbol, dir=DATA_PATH):
        path = levermann_pickle_path(symbol)
        return pickle.load(open(path, "rb"))


class EvaluationResult(object):
    def __init__(self, points, eval_date):
        self.points = points
        self.date = eval_date


class Levermann(object):
    def __init__(self, stock):
        self.stock = stock

        self.evaluation_result = []
        self.roe = None
        self.equity_ratio = None
        self.ebit_margin = None
        self.earning_growth = None
        self.three_month_reversal = None
        self.momentum = None
        self.quote_chg_6month = None
        self.quote_chg_1year = None
        self.earning_revision = None
        self.quarterly_figures_reaction = None
        self.analyst_rating = None
        self.five_years_price_earnings_ratio = None
        self.price_earnings_ratio = None

        if ".de" not in self.stock.symbol.lower():
            raise NotSupportedError("Only DAX Stocks are supported."
                                    " The stock symbol has to end in .de")

        if self.stock.market_cap < (5 * 10**9):
            raise NotSupportedError("Only stocks with large market cap"
                                    " (>=5*10^9) are supported."
                                    " %s < %s" % (self.stock.market_cap,
                                                  5*10**9))

        self.reference_index = "DAX"

    def evaluate(self):
        points = 0
        points += self.eval_roe()
        points += self.eval_ebit_margin()
        points += self.eval_equity_ratio()
        points += self.eval_price_earnings_ratio()
        points += self.eval_five_years_price_earnings_ratio()

        points += self.eval_analyst_rating()
        points += self.eval_quarterly_figures_reaction()
        points_6month_chg = self.eval_quote_chg_6month()
        points_1year_chg = self.eval_quote_chg_1year()
        points += points_6month_chg
        points += points_1year_chg

        points += self.eval_momentum(points_6month_chg, points_1year_chg)
        points += self.eval_three_month_reversal()
        points += self.eval_earning_growth()
        points += self.eval_earning_revision()

        self.evaluation_result.append(EvaluationResult(points, date.today()))

        print("Points: %s" % points)

        return points

    def eval_earning_growth(self):
        logger.debug("Evaluating past and prognosed"
                     " earning growth")
        eps_cur_year = self.stock.eps[THIS_YEAR][-1].value
        eps_next_year = self.stock.eps[THIS_YEAR + 1][-1].value

        chg = ((eps_cur_year.amount / eps_next_year.amount) - 1) * 100
        logger.debug("EPS current year: %s\n"
                     "EPS next year: %s\n"
                     "Change: %s%%" % (eps_cur_year, eps_next_year, chg))

        if chg >= -5 and chg <= 5:
            logger.debug("Earning growth change >=-5%%, <=5% => 0 Points")
            points = 0
        elif eps_cur_year < eps_next_year:
            logger.debug("Earning growth change EPS next year > EPS current"
                         " year => 1 Points")
            points = 1
        elif eps_cur_year > eps_next_year:
            logger.debug("Earning growth change EPS next year < EPS current"
                         " year => -1 Points")
            points = -1

        self.earning_growth = CriteriaRating(chg, points)

        return points

    def _calc_ref_index_comp(self, date):
        # compare quote of stock with the quote of the reference index at the
        # last day of the month
        d = last_weekday_of_month(date)
        ref_quote = yahoo.stock_quote(self.reference_index, d)
        quote = yahoo.stock_quote(self.stock.symbol, d)

        prev_month_date = last_weekday_of_month(prev_month(date))
        prev_ref_quote = yahoo.stock_quote(self.reference_index,
                                               prev_month_date)
        prev_quote = yahoo.stock_quote(self.stock.symbol, prev_month_date)

        ((prev_quote / quote) - 1) * 100
        ((prev_ref_quote / ref_quote) - 1) * 100

        return prev_quote - prev_ref_quote

    def eval_three_month_reversal(self):
        d = prev_month(date.today())
        m1_diff = self._calc_ref_index_comp(d)

        d = prev_month(d)
        m2_diff = self._calc_ref_index_comp(d)

        d = prev_month(d)
        m3_diff = self._calc_ref_index_comp(d)

        if (m1_diff > 0 and m2_diff > 0 and m3_diff > 0):
            points = -1
        elif (m1_diff < 0 and m2_diff < 0 and m3_diff < 0):
            points = 1
        else:
            points = 0

        self.three_month_reversal = CriteriaRating((m1_diff, m2_diff, m3_diff),
                                                   points)

        return points

    def eval_momentum(self, points_6month_chg, points_1year_chg):
        if points_6month_chg == 1 and (points_1year_chg <= 0):
            points = 1
        elif points_6month_chg == -1 and (points_1year_chg >= 0):
            points = -1
        else:
            points = 0

        self.momentum = CriteriaRating((points_6month_chg, points_1year_chg),
                                       points)
        return points

    def _calc_quite_chg_points(self, chg):
        if chg >= -5 and chg <= 5:
            return 0
        elif chg < -5:
            return -1
        elif chg > 5:
            return 1

    def _eval_quote_chg_daydiff(self, days_diff):
        before_date = closest_weekday(date.today() - timedelta(days=days_diff))
        before_quote = yahoo.stock_quote(self.stock.symbol, before_date)

        chg = ((float(self.stock.quote.amount) / before_quote) - 1) * 100
        return (chg, self._calc_quite_chg_points(chg))

    def eval_quote_chg_6month(self):
        chg, points = self._eval_quote_chg_daydiff(182)

        self.quote_chg_6month = CriteriaRating(chg, points)

        return points

    def eval_quote_chg_1year(self):
        chg, points = self._eval_quote_chg_daydiff(365)

        self.quote_chg_1year = CriteriaRating(chg, points)

        return points

    def _calc_eps_chg(self, eps_list):
        assert len(eps_list) > 2
        latest = eps_list[-1]
        min_date = latest.update_date - timedelta(days=6*30)

        other = eps_list[-2]
        # TODO: ensure that eps_list is always ordered on update_time
        if not eps_list[-2].update_date >= min_date:
            return None

        return ((latest.value / other) - 1) * 100

    def _calc_earning_rev_points(self, chg):
        if chg >= -5 and chg <= 5:
            return 0
        elif chg > 5:
            return 1
        elif chg < -5:
            return -1

    def eval_earning_revision(self):
        cur_year_eps = self.stock.eps[THIS_YEAR]
        next_year_eps = self.stock.eps[THIS_YEAR + 1]

        if len(cur_year_eps) < 2 or len(next_year_eps) < 2:
            self.earning_revision = CriteriaRating((None, None), 0)
            return 0

        cur_year_chg = self._calc_eps_chg(cur_year_eps)
        next_year_chg = self._calc_eps_chg(next_year_eps)

        cur_year_points = self._calc_earning_rev_points(cur_year_chg)
        next_year_points = self._calc_earning_rev_points(next_year_chg)

        psum = cur_year_points + next_year_points

        if cur_year_points == 0 and next_year_points == 0:
            points = 0
        elif psum >= 1:
            points = 1
        elif psum <= -1:
            points = -1

        self.earning_revision = CriteriaRating((cur_year_points,
                                                next_year_points), points)

        return points

    def eval_quarterly_figures_reaction(self):
        logger.debug("Evaluating stock reaction on"
                     "quarterly figures")
        qf_date = self.stock.last_quarterly_figures_date
        qf_prev_day = prev_weekday(self.stock.last_quarterly_figures_date)

        qf_previous_day_quote = yahoo.stock_quote(self.stock.symbol,
                                                      qf_prev_day)
        qf_day_quote = yahoo.stock_quote(self.stock.symbol, qf_date)
        qf_reaction = ((qf_day_quote / qf_previous_day_quote) - 1) * 100

        ref_index_quote = yahoo.stock_quote(self.reference_index, qf_date)
        ref_previous_index_quote = yahoo.stock_quote(self.reference_index,
                                                         qf_prev_day)
        ref_index_chg = (((ref_index_quote / ref_previous_index_quote) - 1) *
                         100)

        rel_qf_reaction = qf_reaction - ref_index_chg

        logger.debug("Stock reaction to quarterly figure release: %s%%,"
                     "%s change on quarterly figures release date: %s%%"
                     % (qf_reaction, self.reference_index, ref_index_chg))

        if rel_qf_reaction >= -1 and rel_qf_reaction < 1:
            logger.debug("Relative Stock reaction to quarterly figure release"
                         " is %s%%" ", >= -1%%, <1%% => 0 Points" %
                         rel_qf_reaction)
            points = 0
        elif rel_qf_reaction >= 1:
            logger.debug("Relative Stock reaction to quarterly figure release"
                         " is %s%%" ", >1%% => 1 Points" % rel_qf_reaction)
            points = 1
        else:
            logger.debug("Relative Stock reaction to quarterly figure release"
                         " is %s%%" ", <-1%% => -1 Points" % rel_qf_reaction)
            points = -1

        self.quarterly_figures_reaction = CriteriaRating(rel_qf_reaction,
                                                         points)

        return points

    def eval_analyst_rating(self):
        BUY_LOWER_BOUND = 1
        BUY_UPPER_BOUND = 2
        HOLD_LOWER_BOUND = 2
        HOLD_UPPER_BOUND = 4
        SELL_LOWER_BOUND = 4
        SELL_UPPER_BOUND = 5

        # Leverman uses the analyst rating for large caps stock as contra
        # indicator, therefore we inverse their recommendation

        r = self.stock.analyst_recommendation_rating

        if r is None or (r >= HOLD_LOWER_BOUND and r < HOLD_UPPER_BOUND):
            points = 0
        elif r >= BUY_LOWER_BOUND and r < BUY_UPPER_BOUND:
            points = -1
        elif r >= SELL_LOWER_BOUND and r <= SELL_UPPER_BOUND:
            points = 1
        else:
            raise InvalidValueError("Invalid rating value: '%s'" % r)

        self.analyst_rating = CriteriaRating(r, points)

        return points

    def eval_five_years_price_earnings_ratio(self):
        per = self.stock.price_earnings_ratio_5year().amount
        logger.debug("Evaluating 5year PER: %s" % (per))

        if per < 12:
            logger.debug("5 year PER <12: 1 Points")
            points = 1
        elif per >= 12 and per <= 16:
            logger.debug("5 year PER >=12, <=16: 0 Points")
            points = 0
        else:
            logger.debug("5 year PER >16: -1 Points")
            points = -1

        self.five_years_price_earnings_ratio = CriteriaRating(per, points)

        return points

    def eval_price_earnings_ratio(self):
        per = self.stock.price_earnings_ratio().amount
        logger.debug("Evaluating PER: %s" % (per))

        if per < 12:
            logger.debug("PER <12: 1 Points")
            points = 1
        elif per >= 12 and per <= 16:
            logger.debug("PER >=12, <=16: 0 Points")
            points = 0
        else:
            logger.debug("PER >16: -1 Points")
            points = -1

        self.price_earnings_ratio = CriteriaRating(per, points)

        return points

    def eval_roe(self):
        year = LAST_YEAR
        if year not in self.stock.roe:
            year -= 1
            logger.debug("ROE for year year %s"
                         " not set. Evaluation RoE "
                         " of year %s instead" % (LAST_YEAR, year))
        roe = self.stock.roe[year]

        logger.debug("Evaluating RoE (%s): %s%%" % (year, roe))
        if roe < 10:
            logger.debug("ROE <10%: -1 Points")
            points = -1
        elif roe >= 10 and roe <= 20:
            logger.debug("ROE >=10%, <=20%: 0 Points")
            points = 0
        elif roe > 20:
            logger.debug("ROE >20%: 1 Point")
            points = 1

        self.roe = CriteriaRating(roe, points)
        return points

    def eval_equity_ratio(self):
        last_year = LAST_YEAR

        if last_year not in self.stock.equity_ratio:
            last_year -= 1
            logger.debug("Equity ratio for year year %s"
                         " not set. Evaluation Equity Ratio"
                         " of year %s instead" % (LAST_YEAR, last_year))

        equity_ratio = self.stock.equity_ratio[last_year]

        logger.debug("Evaluating equity ratio (%s): %s%%" % (last_year,
                                                             equity_ratio))
        if equity_ratio < 15:
            logger.debug("Equity Ratio <10%: -1 Points")
            points = -1
        elif equity_ratio >= 15 and equity_ratio <= 25:
            logger.debug("Equity Ratio >=15%, <=25%: 0 Points")
            points = 0
        elif equity_ratio > 25:
            logger.debug("Equity Ratio >25%: 1 Point")
            points = 1

        self.equity_ratio = CriteriaRating(equity_ratio, points)

        return points

    def eval_ebit_margin(self):
        last_year = LAST_YEAR
        if last_year not in self.stock.ebit_margin:
            last_year -= 1
            logger.debug("Ebit margin for year %s unknown."
                         " Evaluating margin of year %s"
                         " instead" % (LAST_YEAR, last_year))

        ebit_margin = self.stock.ebit_margin[last_year]

        logger.debug("Evaluating EBIT-Margin %s" % ebit_margin)
        if ebit_margin < 6:
            logger.debug("EBIT-Margin <6%: -1 Points")
            points = -1
        elif ebit_margin >= 6 and ebit_margin <= 12:
            logger.debug("EBIT-Margin >=6%, <=12%: 0 Points")
            points = 0
        elif ebit_margin > 12:
            logger.debug("EBIT-Margin >12%: 1 Points")
            points = 1

        self.ebit_margin = CriteriaRating(ebit_margin, points)

        return points

    def save(self, dir=DATA_PATH):
        path = levermann_pickle_path(self.stock.symbol, dir)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    def __str__(self):
        eval_result = self.evaluation_result[-1]

        s = str(self.stock)
        s += "{:<35} {:<25}\n".format("Last Evaluation Date:",
                                      "%s" % eval_result.date)
        s += "\n"
        s += "{:<35} {:<25} | {} Points\n".format("RoE:",
                                                  "%s%%" % self.roe.value,
                                                  self.roe.points)
        s += "{:<35} {:<25} | {} Points\n".format("Equity Ratio:", "%s%%" %
                                                  self.equity_ratio.value,
                                                  self.equity_ratio.points)
        s += "{:<35} {:<25} | {} Points\n".format("EBIT Margin:", "%s%%" %
                                                  self.ebit_margin.value,
                                                  self.ebit_margin.points)
        s += "{:<35} {:<25} | {} Points\n".format("%s vs. %s EPS growth:" %
                                                  (THIS_YEAR, THIS_YEAR + 1),
                                                  "%s%%" %
                                                  self.earning_growth.value,
                                                  self.earning_growth.points)
        s += "{:<35} {:<25} | {} Points\n".format("3 month reversal:",
                                                  "%.2f%%, %.2f%%, %.2f%%" %
                                                  self.three_month_reversal.value[::-1],
                                                  self.three_month_reversal.points)
        s += "{:<35} {:<25} | {} Points\n".format("Stock momentum (6m,"
                                                  "1y chg points):",
                                                  "%s Points, %s Points" %
                                                  self.momentum.value,
                                                  self.momentum.points)
        s += "{:<35} {:<25} | {} Points\n".format("6 month quote movement:",
                                                  "%.2f%%" %
                                                  self.quote_chg_6month.value,
                                                  self.quote_chg_6month.points)
        s += "{:<35} {:<25} | {} Points\n".format("1 year quote movement:",
                                                  "%.2f%%" %
                                                  self.quote_chg_1year.value,
                                                  self.quote_chg_1year.points)
        s += "{:<35} {:<25} | {} Points\n".format("Earning revision "
                                                  "(6m, 1y points):",
                                                  "%s Points, %s Points" %
                                                  self.earning_revision.value,
                                                  self.earning_revision.points)
        s += "{:<35} {:<25} | {} Points\n".format("Quarterly figures release"
                                                  " reaction:",
                                                  "%.2g%%" %
                                                  self.quarterly_figures_reaction.value,
                                                  self.quarterly_figures_reaction.points)
        s += "{:<35} {:<25} | {} Points\n".format("Yahoo analyst rating",
                                                  self.analyst_rating.value,
                                                  self.analyst_rating.points)
        s += "{:<35} {:<25.2f} | {} Points\n".format("Price earnings ratio",
                                                     self.price_earnings_ratio.value,
                                                     self.price_earnings_ratio.points)
        s += "{:<35} {:<25.2f} | {} Points\n".format("5y price earnings ratio",
                                                     self.five_years_price_earnings_ratio.value,
                                                     self.five_years_price_earnings_ratio.points)
        s += "\n"

        s += "{:<35} {:<25} | {} Points\n".format("Total Levermann Points:",
                                                  "",
                                                  eval_result.points)
        return s
