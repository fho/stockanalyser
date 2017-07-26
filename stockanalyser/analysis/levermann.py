import logging
import calendar
import pickle
from datetime import date, timedelta
import datetime
from stockanalyser.data_source import yahoo, alphavantage
from stockanalyser.exceptions import NotSupportedError, InvalidValueError
from stockanalyser.config import *
from stockanalyser import fileutils
from stockanalyser.stock import Cap
from enum import Enum, unique

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


@unique
class Recommendation(Enum):
    BUY = 1
    SELL = 2
    NONE = 3


class LevermannResult(object):
    def __init__(self):
        self.timestamp = datetime.datetime.now()

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
        self._score = None

    def __str__(self):
        s = "{:<35} {:<25}\n".format("Last Evaluation Date:", "%s" %
                                     self.timestamp)
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
        s += "{:<35} {:<25} | {} Points\n".format("%s vs. %s Earning growth:" %
                                                  (THIS_YEAR, THIS_YEAR + 1),
                                                  "%.2f%%" %
                                                  self.earning_growth.value,
                                                  self.earning_growth.points)
        if self.three_month_reversal.value[::-1][0] != None:
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
                                                  str(self.analyst_rating.value or ""),
                                                  self.analyst_rating.points)
        s += "{:<35} {:<25.2f} | {} Points\n".format("Price earnings ratio",
                                                     self.price_earnings_ratio.value,
                                                     self.price_earnings_ratio.points)
        s += "{:<35} {:<25.2f} | {} Points\n".format("5y price earnings ratio",
                                                     self.five_years_price_earnings_ratio.value,
                                                     self.five_years_price_earnings_ratio.points)
        s += "\n"

        s += "{:<35} {:<25} | {} Points\n".format("Total Levermann Score:",
                                                  "", self.score)

        return s

    @property
    def score(self):
        if self._score is None:
            self._score = (self.roe.points + self.equity_ratio.points +
                           self.ebit_margin.points +
                           self.earning_growth.points +
                           self.three_month_reversal.points +
                           self.momentum.points +
                           self.quote_chg_6month.points +
                           self.quote_chg_1year.points +
                           self.earning_revision.points +
                           self.quarterly_figures_reaction.points +
                           self.analyst_rating.points +
                           self.five_years_price_earnings_ratio.points +
                           self.price_earnings_ratio.points)
        return self._score


def levermann_pickle_path(symbol, dir=DATA_PATH):
        filename = fileutils.to_pickle_filename(symbol + ".levermann")
        path = os.path.join(dir, filename)
        return path


def unpickle_levermann_sym(symbol, dir=DATA_PATH):
        path = levermann_pickle_path(symbol)
        return unpickle_levermann(path)


def unpickle_levermann(path):
        l = pickle.load(open(path, "rb"))
        logger.debug("Unpickled Levermann Analysis for Stock: %s from '%s'" %
                     (l.stock.symbol, path))
        return l


class EvaluationResult(object):
    def __init__(self, points, eval_date):
        self.points = points
        self.date = eval_date


class Levermann(object):
    def __init__(self, stock):
        self.stock = stock
        self.evaluation_results = []

        if self.stock.cap_type == Cap.LARGE:
            self.reference_index = "^GDAXI"
        elif self.stock.cap_type == Cap.MID:
            self.reference_index = "^MDAXI"
        elif self.stock.cap_type == Cap.SMALL:
            self.reference_index = "^SDAXI"
        else:
            raise NotSupportedError("Only DAX Stocks are supported."
                                    " The stock symbol has to end in .de")

    def evaluate(self):
        logger.info("Creating Levermann Analysis for %s" % self.stock.symbol)
        result = LevermannResult()

        result.roe = self.eval_roe()
        result.ebit_margin = self.eval_ebit_margin()
        result.equity_ratio = self.eval_equity_ratio()
        result.price_earnings_ratio = self.eval_price_earnings_ratio()
        result.five_years_price_earnings_ratio = \
            self.eval_five_years_price_earnings_ratio()
        result.analyst_rating = self.eval_analyst_rating()
        result.quarterly_figures_reaction = \
            self.eval_quarterly_figures_reaction()

        result.quote_chg_6month = self.eval_quote_chg_6month()
        result.quote_chg_1year = self.eval_quote_chg_1year()
        result.momentum = self.eval_momentum(result.quote_chg_6month.points,
                                             result.quote_chg_1year.points)

        result.three_month_reversal = self.eval_three_month_reversal()
        result.earning_growth = self.eval_earning_growth()
        result.earning_revision = self.eval_earning_revision()

        if self.evaluation_results:
            last = self.evaluation_results[-1]
            if ((last.timestamp > (datetime.datetime.now() -
                 datetime.timedelta(days=7))) and last.score == result.score):
                logger.debug("Old Levermann analysis:\n%s\n"
                             "New Levermann anylsis: \n%s" %
                             (str(last), str(result)))
                logger.info("Previous Levermann analysis is younger than 1"
                            " week and\nLevermann score hasn't changed."
                            "New analysis data is not stored.")
                return False

        self.evaluation_results.append(result)

        return True

    def outdated(self):
        if not self.evaluation_results:
            return True

        last = self.evaluation_results[-1]
        if (last.timestamp < (datetime.datetime.now() -
                              datetime.timedelta(days=3))):
            return True
        return False

    def eval_earning_growth(self):
        logger.debug("Evaluating earning growth")
        #TODO: ensure that eps is always sorted in stock

        eps_cur_year = self.stock.eps[THIS_YEAR][-1].value
        eps_next_year = self.stock.eps[THIS_YEAR + 1][-1].value

        chg = ((eps_next_year.amount / eps_cur_year.amount) - 1) * 100
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

        return CriteriaRating(chg, points)

    def _calc_ref_index_comp(self, date):
        # compare quote of stock with the quote of the reference index at the
        # last day of the month
        d = last_weekday_of_month(date)
        prev_month_date = last_weekday_of_month(prev_month(date))

        quote = alphavantage.stock_quote(self.stock.symbol, d)
        prev_quote = alphavantage.stock_quote(self.stock.symbol, prev_month_date)
        q_diff = ((quote / prev_quote) - 1) * 100

        ref_quote = alphavantage.stock_quote(self.reference_index, d)
        prev_ref_quote = alphavantage.stock_quote(self.reference_index,
                                           prev_month_date)
        ref_q_diff = ((ref_quote / prev_ref_quote) - 1) * 100

        logger.debug("Comparing Stock with reference index. "
                     "(%s vs %s) Stock: %s vs %s = %s%%,"
                     "Ref. Index.: %s vs %s = %s%%" %
                     (d, prev_month_date, quote, prev_quote, q_diff,
                      ref_quote, prev_ref_quote, ref_q_diff))

        return q_diff - ref_q_diff

    def eval_three_month_reversal(self):
        logger.debug("Evaluating 3 month reversal")

        if self.stock.cap_type != Cap.LARGE:
            return CriteriaRating((None, None, None), 0)
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

        return CriteriaRating((m1_diff, m2_diff, m3_diff), points)

    def eval_momentum(self, points_6month_chg, points_1year_chg):
        if points_6month_chg == 1 and (points_1year_chg <= 0):
            points = 1
        elif points_6month_chg == -1 and (points_1year_chg >= 0):
            points = -1
        else:
            points = 0

        return CriteriaRating((points_6month_chg, points_1year_chg), points)

    def _calc_quite_chg_points(self, chg):
        if chg >= -5 and chg <= 5:
            return 0
        elif chg < -5:
            return -1
        elif chg > 5:
            return 1

    def _eval_quote_chg_daydiff(self, days_diff):
        before_date = closest_weekday(date.today() - timedelta(days=days_diff))
        before_quote = alphavantage.stock_quote(self.stock.symbol, before_date)

        chg = ((float(self.stock.quote.amount) / before_quote) - 1) * 100
        return (chg, self._calc_quite_chg_points(chg))

    def eval_quote_chg_6month(self):
        chg, points = self._eval_quote_chg_daydiff(182)

        return CriteriaRating(chg, points)

    def eval_quote_chg_1year(self):
        chg, points = self._eval_quote_chg_daydiff(365)

        return CriteriaRating(chg, points)

    def _calc_eps_chg(self, eps_list):
        assert len(eps_list) >= 2
        latest = eps_list[-1]
        other = eps_list[-2]
        logger.debug("EPS vals: latest: %s, other: %s" % (latest, other))

        return ((latest.value.amount / other.value.amount) - 1) * 100

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
            return CriteriaRating((None, None), 0)

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

        return CriteriaRating((cur_year_points, next_year_points), points)

    def eval_quarterly_figures_reaction(self):
        logger.debug("Evaluating stock reaction on"
                     "quarterly figures")
        qf_date = self.stock.last_quarterly_figures_release_date()
        qf_prev_day = prev_weekday(self.stock.last_quarterly_figures_release_date())

        qf_previous_day_quote = alphavantage.stock_quote(self.stock.symbol,
                                                  qf_prev_day)
        qf_day_quote = alphavantage.stock_quote(self.stock.symbol, qf_date)
        qf_reaction = ((qf_day_quote / qf_previous_day_quote) - 1) * 100

        ref_index_quote = alphavantage.stock_quote(self.reference_index, qf_date)
        ref_previous_index_quote = alphavantage.stock_quote(self.reference_index,
                                                     qf_prev_day)
        ref_index_chg = (((ref_index_quote / ref_previous_index_quote) - 1) *
                         100)

        rel_qf_reaction = qf_reaction - ref_index_chg

        logger.debug("Quarterly figure reaction %s vs %s: "
                     "%s: %s vs %s => %s, %s: %s vs %s => %s," %
                     (qf_date, qf_prev_day, self.stock.symbol, qf_day_quote,
                      qf_previous_day_quote, qf_reaction, self.reference_index,
                      ref_index_quote, ref_previous_index_quote,
                      ref_index_chg))

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

        return CriteriaRating(rel_qf_reaction, points)

    def eval_analyst_rating(self):
        if (self.stock.analyst_ratings[0] is None or
            self.stock.analyst_ratings[1] is None or
            self.stock.analyst_ratings[2] is None):
            logger.debug("No analyst rating available")
            return CriteriaRating(None, 0)

        ratings = self.stock.analyst_ratings
        logger.debug("Analyst ratings: %s" % str(ratings))
        score = (((ratings[0] * 1) + (ratings[1] * 2) + (ratings[2] * 3)) /
                 (float(ratings[0]) + ratings[1] + ratings[2]))

        logger.debug("Analyst score: %s" % score)

        # for small caps with less than 5 ratings, the recommendations are
        # followed
        if (self.stock.cap_type == Cap.SMALL and
            (ratings[0] + ratings[1] + ratings[2]) < 5):
            if score >= 1 and score <= 1.5:
                points = 1
            if score > 1.5 and score < 2.5:
                points = 0
            if score >= 2.5:
                points = -1
        else:
        # for other stocks the recommendation is inverted
            if score >= 1 and score <= 1.5:
                points = -1
            if score > 1.5 and score < 2.5:
                points = 0
            if score >= 2.5:
                points = 1

        return CriteriaRating(score, points)

    def eval_five_years_price_earnings_ratio(self):
        per = self.stock.price_earnings_ratio_5year().amount
        logger.debug("Evaluating 5year PER: %s" % (per))

        if per > 0 and per < 12:
            logger.debug("5 year PER <12: 1 Points")
            points = 1
        elif per >= 12 and per <= 16:
            logger.debug("5 year PER >=12, <=16: 0 Points")
            points = 0
        else:
            logger.debug("5 year PER >16: -1 Points")
            points = -1

        return CriteriaRating(per, points)

    def eval_price_earnings_ratio(self):
        per = self.stock.price_earnings_ratio().amount
        logger.debug("Evaluating PER: %s" % (per))

        if per > 0 and per < 12:
            logger.debug("PER <12: 1 Points")
            points = 1
        elif per >= 12 and per <= 16:
            logger.debug("PER >=12, <=16: 0 Points")
            points = 0
        else:
            logger.debug("PER >16: -1 Points")
            points = -1

        return CriteriaRating(per, points)

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

        return CriteriaRating(roe, points)

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

        return CriteriaRating(equity_ratio, points)

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

        return CriteriaRating(ebit_margin, points)

    def save(self, dir=DATA_PATH):
        path = levermann_pickle_path(self.stock.symbol, dir)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    def short_summary_header(self):
        s = ("| {:<25} | {:<14} | {:<14} | {:<6} |".\
                format("Name", "Prev Score (Date)", "Last Score (Date)",
                       "Advise"))
        s += "\n"
        s += "-" * 78
        return s

    def short_summary_footer(self):
        return "-" * 78

    def short_summary(self):
        r = self.evaluation_results[-1]
        r_prev = None
        r_prev_ts = "N/A"
        r_prev_score = "N/A"
        if len(self.evaluation_results) > 1:
            r_prev = self.evaluation_results[-2]
            r_prev_ts = r_prev.timestamp.strftime("%x")
            r_prev_score = r_prev.score

        r_ts = r.timestamp.strftime("%x")

        s = ("| {:<25} | {:<6} ({:<8}) | {:<6} ({:<8}) | {:<6} |".\
                format(self.stock.name, r_prev_score,
                       r_prev_ts, r.score, r_ts, self.recommendation().name))

        return s

    def __str__(self):
        if not self.evaluation_results:
            return "No Analysis exist"

        r = self.evaluation_results[-1]

        s = str(self.stock)
        s += str(r)
        return s

    def recommendation(self):
        if (len(self.evaluation_results) >= 2 and
            (self.evaluation_results[-1].score -
             self.evaluation_results[-2].score) <= -2):
            return Recommendation.SELL

        if self.stock.cap_type == Cap.LARGE:
            if self.evaluation_results[-1].score <= 2:
                return Recommendation.SELL
            if self.evaluation_results[-1].score >= 4:
                return Recommendation.BUY
            return Recommendation.NONE

        if self.evaluation_results[-1].score <= 4:
            return Recommendation.SELL
        if self.evaluation_results[-1].score >= 7:
            return Recommendation.BUY

        return Recommendation.NONE


if __name__ == "__main__":
    from pprint import pprint
    from stockanalyser.stock import Stock
    """"
    logging.basicConfig(level=logging.DEBUG)
    s = Stock("VOW.DE")
    s.onvista_fundamental_url = "http://www.onvista.de/aktien/Volkswagen-ST-Aktie-DE0007664005"
    s.finanzen_net_url = "http://www.finanzen.net/termine/Volkswagen"
    s.update_stock_info()
    leverman = Levermann(stock=s)
    pprint(leverman.evaluate())
    """
    
    s = Stock("SIE.DE")
    s.onvista_fundamental_url = "http://www.onvista.de/aktien/Siemens-Aktie-DE0007236101"
    s.finanzen_net_url = "http://www.finanzen.net/termine/Siemens"
    s.update_stock_info()
    leverman = Levermann(stock=s)
    pprint(leverman.evaluate())


    s2 = Stock("MUV2.DE")
    s2.onvista_fundamental_url = "http://www.onvista.de/aktien/Muenchener-Rueck-Aktie-DE0008430026"
    s2.update_stock_info()
