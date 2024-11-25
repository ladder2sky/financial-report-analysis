import numpy as np
from conf.setting import fmt, PROFIT_SHEET_FIELD_FILENAME, BALANCE_SHEET_FIELD_FILENAME
import pandas as pd
import os
base_path = os.path.dirname(os.path.dirname(__file__))


def get_profit_sheet(ts_pro, ts_code, start_date, end_date, end_type):
    """
    :param ts_pro, tushare handler.
    :param ts_code, 需要查询的股票代码
    :param start_date, 查询的开始年份
    :param end_date, 查询的结束年份
    :param end_type, 查询的财报期数
    :return:
    步骤：
    见项目分步骤的注释
    """
    profit_sheet_field_df = read_field_file(PROFIT_SHEET_FIELD_FILENAME, ['profit_order', 'value_order'])
    profit_sheet_field = list(profit_sheet_field_df.index)
    # blank是自己添加的字段，tushare中并没有此field, 因此从参数字符串剔除掉。
    profit_sheet_field = [x for x in profit_sheet_field if not 'blank' in x]
    profit_df = ts_pro.income(ts_code=ts_code, start_date=start_date.strftime(fmt), end_date=end_date.strftime(fmt),
                    fields=','.join(profit_sheet_field))
    # 删除重复的报告列
    profit_df = drop_duplicated_report(profit_df).T

    # 将报告模板和原始报告拼接，以获得项目的中文名称
    profit_df = pd.concat([profit_sheet_field_df,profit_df], axis=1)
    profit_df = profit_df[profit_df['profit_order']<32767]

    # 删除掉原始报告中不会在利润表中显示的无用条目
    profit_df.drop(columns=['profit_order', 'value_order'], inplace=True)

    # 重新设置列，以报告期为列名
    clist = profit_df.loc['end_date']
    profit_df.columns = clist
    profit_df.drop(index='end_date', inplace=True)
    # 对2018年前的信用损失数据进行正负号修正, 重命名
    profit_df = profit_data_rectify(profit_df)
    profit_df.rename(columns={'报告期':'条目'}, inplace=True)
    # 对营业利润准确性进行校验
    profit_df = verify_profit_sheet(profit_df)
    return profit_df


def verify_profit_sheet(df):
    clist = list(df.columns)[1:]
    df.index.name = 'Verified'
    for col in clist:
        df_col = df[col]
        df_col = df_col.infer_objects(copy=False)
        df_col.fillna(0, inplace=True)
        op_profit_gap = df_col['revenue'] + df_col['int_income'] + df_col['prem_earned'] + df_col['comm_income']- \
                        df_col['oper_cost'] - df_col['int_exp'] - df_col['comm_exp'] - df_col['biz_tax_surchg'] - \
                        df_col['sell_exp'] - df_col['admin_exp'] - df_col['rd_exp'] - df_col['fin_exp'] + \
                        df_col['oth_income'] + df_col['invest_income'] + df_col['forex_gain'] + \
                        df_col['net_expo_hedging_benefits'] + df_col['fv_value_chg_gain'] + \
                        df_col['credit_impa_loss'] + df_col['assets_impair_loss'] + \
                        df_col['asset_disp_income'] - df_col['operate_profit']
        if int(op_profit_gap) != 0:
            df.index.name = col
            break
    return df


def drop_duplicated_report(df):
    """获取的财务报告中存在重复项。去重原则，优先保留update_flag为1的报告"""
    df.sort_values(by='update_flag', ascending=False, inplace=True)
    df.drop_duplicates(subset = 'end_date', keep='first', inplace=True)
    df.sort_values(by='end_date', ascending=True, inplace=True)
    return df

def profit_data_rectify(profit_df):
    """2018年以前（含2018）信用减值损失的数值正负号相反，需要修正过来"""
    clist = list(profit_df.columns)
    year_before_2019 = [x for x in clist[1:] if int(x[:6]) <= 201903]
    # print(year_before_2019) 调试用，打印小于2019年的财报列名
    for col in year_before_2019:
        if pd.isna(profit_df.loc['credit_impa_loss', col]):
            profit_df.loc['credit_impa_loss', col] = 0
        else:
            profit_df.loc['credit_impa_loss', col] = -profit_df.loc['credit_impa_loss', col]

        if pd.isna(profit_df.loc['assets_impair_loss', col]):
            profit_df.loc['assets_impair_loss', col] = 0
        else:
            profit_df.loc['assets_impair_loss', col] = -profit_df.loc['assets_impair_loss', col]
    return profit_df

def get_cash_flow_sheet():
    pass


def get_balance_sheet(ts_pro, ts_code, start_date, end_date, end_type=5):
    balance_sheet_field_df = read_field_file(BALANCE_SHEET_FIELD_FILENAME, ['bal_order', 'ass_cap_order'])
    balance_sheet_field_list = list(balance_sheet_field_df.index)
    # blank是自己添加的字段，tushare中并没有此field, 因此从参数字符串剔除掉。
    balance_sheet_field_list = [x for x in balance_sheet_field_list if not 'blank' in x]
    balance_df = ts_pro.balancesheet(ts_code=ts_code, start_date=start_date.strftime(fmt), end_date=end_date.strftime(fmt),
                              fields=','.join(balance_sheet_field_list))
    # 删除重复的报告列
    balance_df = drop_duplicated_report(balance_df).T

    # 将报告模板和原始报告拼接，以获得项目的中文名称
    balance_df = pd.concat([balance_sheet_field_df, balance_df], axis=1)
    # 删除多余的列
    balance_df = balance_df[balance_df['bal_order'] < 32767]

    # 删除掉原始报告中不会在利润表中显示的无用条目
    balance_df.drop(columns=['bal_order', 'ass_cap_order'], inplace=True)

    # 重新设置列，以报告期为列名
    clist = balance_df.loc['end_date']
    balance_df.columns = clist
    balance_df.drop(index='end_date', inplace=True)

    balance_df = report_period_filter(balance_df, end_type)

    #对数据进行校验，校验结果添加到表1行1列
    balance_df = verify_balance_sheet(balance_df)
    return balance_df

def verify_balance_sheet(df):
    clist = list(df.columns)[1:]
    df.index.name = 'Verified'
    prefix = ''

    for col in clist:
        ss = pd.Series(df[col])
        ss = ss.infer_objects(copy=False)
        ss.fillna(0, inplace=True)
        liquid_asset_v = int(
            ss.money_cap +
            ss.sett_rsrv +
            ss.loanto_oth_bank_fi +
            ss.trad_asset +
            ss.deriv_assets +
            ss.notes_receiv +
            ss.accounts_receiv +
            ss.receiv_financing +
            ss.prepayment +
            ss.premium_receiv +
            ss.reinsur_receiv +
            ss.reinsur_res_receiv +
            ss.oth_receiv +
            ss.int_receiv +
            ss.div_receiv +
            ss.pur_resale_fa +
            ss.inventories +
            ss.contract_assets +
            ss.hfs_assets +
            ss.nca_within_1y +
            ss.oth_cur_assets -
            ss.total_cur_assets
        )
        illiquid_asset_v = int(
            ss.decr_in_disbur +
            ss.fa_avail_for_sale +
            ss.debt_invest +
            ss.oth_debt_invest +
            ss.lt_rec +
            ss.lt_eqt_invest +
            ss.oth_eq_invest +
            ss.oth_illiq_fin_assets +
            ss.invest_real_estate +
            ss.fix_assets +
            ss.cip +
            ss.produc_bio_assets +
            ss.oil_and_gas_assets +
            ss.use_right_assets +
            ss.intan_assets +
            ss.r_and_d +
            ss.goodwill +
            ss.lt_amor_exp +
            ss.defer_tax_assets +
            ss.oth_nca -
            ss.total_nca
        )

        liquid_debt_v = int(
            ss.st_borr +
            ss.cb_borr +
            ss.loan_oth_bank +
            ss.trading_fl +
            ss.notes_payable +
            ss.deriv_liab +
            ss.acct_payable +
            ss.adv_receipts +
            ss.contract_liab +
            ss.sold_for_repur_fa +
            ss.depos_ib_deposits +
            ss.acting_trading_sec +
            ss.acting_uw_sec +
            ss.payroll_payable +
            ss.taxes_payable +
            ss.oth_payable +
            ss.int_payable +
            ss.div_payable +
            ss.comm_payable +
            ss.payable_to_reinsurer +
            ss.hfs_sales +
            ss.non_cur_liab_due_1y +
            ss.oth_cur_liab -
            ss.total_cur_liab
        )

        illiquid_debt_v = int(
            ss.rsrv_insur_cont +
            ss.lt_borr +
            ss.bond_payable +
            ss.lease_liab +
            ss.lt_payable +
            ss.lt_payroll_payable +
            ss.estimated_liab +
            ss.defer_inc_non_cur_liab +
            ss.oth_ncl +
            ss.defer_tax_liab -
            ss.total_ncl
        )

        if liquid_asset_v != 0:
            prefix = 'la' + col + prefix
        if illiquid_asset_v !=0:
            prefix  = "ia" + col + prefix
        if liquid_debt_v !=0:
            prefix  = "ld" + col + prefix
        if illiquid_debt_v !=0:
            prefix  = "id" + col + prefix
    if prefix != '':
        df.index.name = prefix

    return df

def read_field_file(filename, na_field_lst):
    """
    :param filename: 读取的财报三张表文件名称
    :param na_field_lst: 需要对值为nan的序列值填充，转换为Int格式。
    :return:
    """
    conf_path = os.path.join(base_path, 'conf')
    full_file_name = os.path.join(conf_path, filename)
    df = pd.read_csv(full_file_name, header=0, index_col=0)

    # 填充nan字段，把序号更改为整数格式
    df.fillna(32767, inplace=True)
    for na_item in na_field_lst:
        df[na_item] = df[na_item].astype(np.int16)
    return df


def report_period_filter(df, report_period):
    new_clist = [list(df.columns)[0]]
    old_clist = list(df.columns)[1:]
    if report_period == 1 :
        magic_str = '0331'
    elif report_period == 2 :
        magic_str = '0630'
    elif report_period == 3 :
        magic_str = '0930'
    else :
        magic_str = '1231'

    for col in old_clist:
        if magic_str in col:
            new_clist.append(col)
    if report_period == 5:
        new_clist.append(old_clist[-1])
    return df[new_clist]

