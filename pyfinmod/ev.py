from math import sqrt
import pandas as pd
from pyfinmod.basic import npv


left_rows = [('Total Assets', 1),
             ('Cash And Cash Equivalents', -1),
             ('Total Current Liabilities', -1),
             ('Short/Current Long Term Debt', 1),
             ('Other Current Liabilities', 1)]

right_rows = [('Total Liabilities', 1),
              ("Total stockholders' equity", +1),
              ('Cash And Cash Equivalents', -1),
              ('Total Current Liabilities', -1),
              ('Short/Current Long Term Debt', 1),
              ('Other Current Liabilities', 1)]


right_rows_no_equity = [('Total Liabilities', 1),
                        ('Cash And Cash Equivalents', -1),
                        ('Total Current Liabilities', -1),
                        ('Short/Current Long Term Debt', 1),
                        ('Other Current Liabilities', 1)]


def _ev(column):
    """
    Uses balance sheet to calculate enterprise value. Works only with YahooFinanceParser
    :param column: Yahoo Finance page parsed to dataframe with pyfinmod.yahoo_finance.YahooFinanceParser
    :return: series of enterprise values by date
    """
    left_sum = sum([column.loc[i]*sign for i, sign in left_rows])
    right_sum = sum([column.loc[i]*sign for i, sign in right_rows])
    return left_sum
 


def get_enterprise_value(dataframe):
    return dataframe.apply(_ev)


def _net_working_capital(column):
    """
    Uses balance sheet to net working capital. Works only with YahooFinanceParser
    :param column: Yahoo Finance page parsed to dataframe with pyfinmod.yahoo_finance.YahooFinanceParser
    :return: series of enterprise values by date
    """
    net_receivables = column['Net Receivables']
    inventory = column['Inventory']
    acc_payable = column['Accounts Payable']
    other_curr_liabilities = column['Other Current Liabilities']
    return net_receivables + inventory - acc_payable - other_curr_liabilities


def get_net_working_capital(dataframe):
    return dataframe.apply(_net_working_capital)


def _ev_em(column):
    return sum([column[i] * sign for i, sign in right_rows_no_equity])


def get_enterprise_value_efficient_market(dataframe, market_cap):
    return dataframe.apply(_ev_em) + market_cap


def get_fcf_from_cscf(income_statement_dataframe, cash_flow_dataframe):
    net_income = cash_flow_dataframe.loc['Net Income']
    income_tax_expence = income_statement_dataframe.loc['Income Tax Expense']
    income_tax_rate = income_tax_expence / (net_income + income_tax_expence)
    cash_paid_for_interest = abs(income_statement_dataframe.loc['Interest Expense'])
    after_tax_net_interest = (1 - income_tax_rate) * cash_paid_for_interest
    res = after_tax_net_interest + \
          cash_flow_dataframe.loc['Total Cash Flow From Operating Activities'] + \
          cash_flow_dataframe.loc['Total Cash Flows From Investing Activities']
    return res


def dcf(fcf, wacc, short_term_growth, long_term_growth):
    latest_fcf_date = fcf.index.max()
    dates = pd.date_range(latest_fcf_date, periods=6, freq='365D')[1:]
    future_cash_flows = [fcf[latest_fcf_date]]
    for i in range(5):
        next_year_fcf = future_cash_flows[-1] * (1 + short_term_growth)
        future_cash_flows.append(next_year_fcf)
    future_cash_flows = future_cash_flows[1:]
    df = pd.DataFrame(data={'fcf': future_cash_flows,
                            'date': dates})
    # df.set_index('date', inplace=True)
    df['terminal value'] = 0
    last_index = df.index[-1]
    last_short_term_fcf = df.at[last_index, 'fcf']
    df.at[last_index, 'terminal value'] = last_short_term_fcf * (1 + long_term_growth) / (
            wacc - long_term_growth)
    df['cash flow'] = df[['fcf', 'terminal value']].apply(sum, axis=1)
    return npv(df, wacc) * sqrt((1 + wacc))
