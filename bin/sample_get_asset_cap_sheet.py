import tushare as ts
import sys
import os
from datetime import *
from core.get_finance_sheet import output_asset_cap_sheet


base_path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(base_path)
from core.get_finance_sheet import get_balance_sheet
from conf.setting import token_str, fmt


if __name__ == '__main__':
    file_name = '002867_bal_2014123120241119.csv'
    db_path = conf_path = os.path.join(base_path, 'db')
    full_file_name = os.path.join(db_path, file_name)
    asset_cap_df = output_asset_cap_sheet(full_file_name)
    asset_cap_file_name = file_name[:6] + '_asset_cap.csv'
    full_asset_cap_file_name= os.path.join(db_path, asset_cap_file_name)
    asset_cap_df.to_csv(full_asset_cap_file_name, encoding='gbk')
    print('资产资本表保存为: {}'.format(full_asset_cap_file_name))
