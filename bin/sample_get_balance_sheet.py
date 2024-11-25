import tushare as ts
import sys
import os
from datetime import *
base_path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(base_path)
from core.get_finance_sheet import get_balance_sheet
from conf.setting import token_str, fmt

test_code = '600741.SH'
t_start_date = date(2015, 3, 24)
t_end_date = date(2024, 11,19)
t_end_type = 5
ts.set_token(token_str)
pro = ts.pro_api()
balance_df = get_balance_sheet(pro, test_code, t_start_date, t_end_date, t_end_type)
#print(list(profit_sheet_field.values()))
db_path = conf_path = os.path.join(base_path, 'db')
file_name = test_code[:6] + '_bal_' + t_start_date.strftime(fmt) + t_end_date.strftime(fmt) +'.csv'
full_file_name = os.path.join(db_path,file_name)
# print(balance_df.head())
balance_df.to_csv(full_file_name, encoding='gbk')