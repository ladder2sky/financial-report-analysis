import tushare as ts
import sys
import os
from datetime import *
base_path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(base_path)
from core.get_finance_sheet import get_cash_flow_sheet
from conf.setting import token_str, fmt


if __name__ == '__main__':
    test_code = '002508.SZ'
    t_start_date = date(2015, 3, 24)
    t_end_date = date(2024, 11, 19)
    t_end_type = 4
    ts.set_token(token_str)
    pro = ts.pro_api()
    cash_flow_df = get_cash_flow_sheet(pro, test_code, t_start_date, t_end_date, t_end_type)

    db_path = conf_path = os.path.join(base_path, 'db')
    file_name = test_code[:6] + '_cf_' + t_start_date.strftime(fmt) + t_end_date.strftime(fmt) + '.csv'
    full_file_name = os.path.join(db_path, file_name)
    cash_flow_df.to_csv(full_file_name, encoding='gbk')