import numpy as np
from conf.setting import fmt, PROFIT_SHEET_FIELD_FILENAME, BALANCE_SHEET_FIELD_FILENAME, CASH_FLOW_SHEET_FIELD_FILENAME
import pandas as pd
import os
base_path = os.path.dirname(os.path.dirname(__file__))


def field_list_filter(df):
    """
    返回tushare参数字段，并过滤掉自己添加的字段
    :param df:
    :return:
    """
    field_list = list(df.index)
    # field_list = [x for x in field_list if not 'blank' in x]
    field_list = [x for x in field_list if not 'sum' in x]
    field_list = [x for x in field_list if not 'title' in x]
    return field_list


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

    # 获取tushare参数字段，并过滤自己添加的字段，从参数字符串剔除掉。
    profit_sheet_field = field_list_filter(profit_sheet_field_df)

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

def get_cash_flow_sheet(ts_pro, ts_code, start_date, end_date, end_type=5):
    cash_flow_sheet_field_df = read_field_file(CASH_FLOW_SHEET_FIELD_FILENAME, ['cf_order'])

    # cash_flow_sheet_field_list = list(cash_flow_sheet_field_df.index)
    # 获取tushare参数字段，并过滤自己添加的字段，从参数字符串剔除掉。
    # cash_flow_sheet_field_list = [x for x in cash_flow_sheet_field_list if not 'blank' in x]
    cash_flow_sheet_field_list = field_list_filter(cash_flow_sheet_field_df)

    cash_flow_df = ts_pro.cashflow(ts_code=ts_code, start_date=start_date.strftime(fmt),
                                     end_date=end_date.strftime(fmt),
                                     fields=','.join(cash_flow_sheet_field_list))
    # 删除重复的报告列
    cash_flow_df = drop_duplicated_report(cash_flow_df).T

    # 将报告模板和原始报告拼接，以获得项目的中文名称
    cash_flow_df = pd.concat([cash_flow_sheet_field_df, cash_flow_df], axis=1)
    # 删除多余的列
    cash_flow_df = cash_flow_df[cash_flow_df['cf_order'] < 32767]

    # 删除掉原始报告中不会在利润表中显示的无用条目
    cash_flow_df.drop(columns=['cf_order'], inplace=True)

    # 重新设置列，以报告期为列名
    clist = cash_flow_df.loc['end_date']
    cash_flow_df.columns = clist
    cash_flow_df.drop(index='end_date', inplace=True)

    # 过滤掉无用的报告期报告
    cash_flow_df = report_period_filter(cash_flow_df, end_type)

    #对数据进行校验，校验结果添加到表1行1列
    cash_flow_df = verify_cash_flow_sheet(cash_flow_df)

    return cash_flow_df


def verify_cash_flow_sheet(df):
    clist = list(df.columns)[1:]
    df.index.name = 'Verified'
    prefix = ''
    for col in clist:
        ss = pd.Series(df[col])
        ss = ss.infer_objects(copy=False)
        ss.fillna(0, inplace=True)
        op_cash_in_v = int(
            ss.c_fr_sale_sg +
            ss.n_depos_incr_fi +
            ss.n_incr_loans_cb +
            ss.n_inc_borr_oth_fi +
            ss.prem_fr_orig_contr +
            ss.n_reinsur_prem +
            ss.n_incr_insured_dep +
            ss.n_incr_disp_tfa +
            ss.ifc_cash_incr +
            ss.n_incr_loans_oth_bank +
            ss.n_cap_incr_repur +
            ss.recp_tax_rends +
            ss.c_fr_oth_operate_a -
            ss.c_inf_fr_operate_a
        )

        op_cash_out_v = int(
            ss.c_paid_goods_s +
            ss.n_incr_clt_loan_adv +
            ss.n_incr_dep_cbob +
            ss.c_pay_claims_orig_inco +
            ss.pay_handling_chrg +
            ss.pay_comm_insur_plcy +
            ss.c_paid_to_for_empl +
            ss.c_paid_for_taxes +
            ss.oth_cash_pay_oper_act -
            ss.st_cash_out_act
        )

        i_cash_in_v = int(
            ss.c_disp_withdrwl_invest +
            ss.c_recp_return_invest +
            ss.n_recp_disp_fiolta +
            ss.n_recp_disp_sobu +
            ss.oth_recp_ral_inv_act -
            ss.stot_inflows_inv_act
        )

        i_cash_out_v = int(
            ss.c_pay_acq_const_fiolta +
            ss.c_paid_invest +
            ss.n_incr_pledge_loan +
            ss.n_disp_subs_oth_biz +
            ss.oth_pay_ral_inv_act -
            ss.stot_out_inv_act
        )

        f_cash_in_v = int(
            ss.c_recp_cap_contrib +
            ss.c_recp_borrow +
            ss.proc_issue_bonds +
            ss.oth_cash_recp_ral_fnc_act -
            ss.stot_cash_in_fnc_act
        )

        f_cash_out_v = int(
            ss.c_prepay_amt_borr +
            ss.c_pay_dist_dpcp_int_exp +
            ss.oth_cashpay_ral_fnc_act -
            ss.stot_cashout_fnc_act
        )
        if op_cash_in_v != 0:
            prefix = 'oi' + col + prefix
        if op_cash_out_v != 0:
            prefix = 'oo' + col + prefix
        if i_cash_in_v != 0:
            prefix = 'ii' + col + prefix
        if i_cash_out_v != 0:
            prefix = 'io' + col + prefix
        if f_cash_in_v != 0:
            prefix = 'fi' + col + prefix
        if f_cash_out_v != 0:
            prefix = 'fo' + col + prefix
    if prefix != '':
        df.index.name = prefix
    return df




def get_balance_sheet(ts_pro, ts_code, start_date, end_date, end_type=5):
    """

    :param ts_pro:
    :param ts_code:
    :param start_date:
    :param end_date:
    :param end_type:1, 一季度；2, 二季度；。。。；5, 年度加最近季度；
    :return:
    """
    balance_sheet_field_df = read_field_file(BALANCE_SHEET_FIELD_FILENAME, ['bal_order', 'ass_cap_order'])
    # balance_sheet_field_list = list(balance_sheet_field_df.index)
    # 获取tushare参数字段，并过滤自己添加的字段，从参数字符串剔除掉。
    # balance_sheet_field_list = [x for x in balance_sheet_field_list if not 'blank' in x]
    balance_sheet_field_list = field_list_filter(balance_sheet_field_df)
    balance_df = ts_pro.balancesheet(ts_code=ts_code, start_date=start_date.strftime(fmt), end_date=end_date.strftime(fmt),
                              fields=','.join(balance_sheet_field_list))
    # 删除重复的报告列
    balance_df = drop_duplicated_report(balance_df).T

    # 将报告模板和原始报告拼接，以获得项目的中文名称
    balance_df = pd.concat([balance_sheet_field_df, balance_df], axis=1)
    # 删除多余的列
    balance_df = balance_df[balance_df['bal_order'] < 32767].sort_values('bal_order', ascending=True)

    # 删除掉原始报告中不会在利润表中显示的无用条目
    balance_df.drop(columns=['bal_order', 'ass_cap_order'], inplace=True)

    # 重新设置列，以报告期为列名
    clist = balance_df.loc['end_date']
    balance_df.columns = clist
    balance_df.drop(index='end_date', inplace=True)

    # 过滤掉无用的报告期报告
    balance_df = report_period_filter(balance_df, end_type)

    #对数据进行校验，校验结果添加到表1行1列
    balance_df = verify_balance_sheet(balance_df)
    return balance_df

def verify_balance_sheet(df):
    """
    对传入的资产负债表进行校验，包括流资产和负债。对于存在的错误，会作为index.name写入表头。
    :param df:
    :return:
    """
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
            ss.fixed_assets_disp +
            ss.const_materials +
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
            ss.long_pay_total +
            ss.lt_payroll_payable +
            ss.estimated_liab +
            ss.defer_inc_non_cur_liab +
            ss.oth_ncl +
            ss.defer_tax_liab -
            ss.total_ncl
        )

        owner_rgt_v = int(
            ss.total_share +
            ss.oth_eqt_tools +
            ss.oth_eqt_tools_p_shr +
            ss.oth_eq_ppbond +
            ss.cap_rese -
            ss.treasury_share +
            ss.oth_comp_income +
            ss.special_rese +
            ss.surplus_rese +
            ss.ordin_risk_reser +
            ss.undistr_porfit +
            ss.minority_int -
            ss.total_hldr_eqy_inc_min_int
        )
        if liquid_asset_v != 0:
            prefix = 'la' + col + prefix
        if illiquid_asset_v !=0:
            prefix  = "ia" + col + prefix
        if liquid_debt_v !=0:
            prefix  = "ld" + col + prefix
        if illiquid_debt_v !=0:
            prefix  = "id" + col + prefix
        if owner_rgt_v !=0:
            prefix = 'or' + col + prefix
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


def output_asset_cap_sheet(balance_sheet_file_name):
    """
    步骤1： 读取资产负债表；
    步骤2： 构建股权价值增加表的结构；
    步骤3： 将资产负债表的数据填入股权价值增加表中；
    步骤4： 对股权价值增加表的数据进行校验；
    步骤5： 返回股权价值增加表的dataframe
    :param balance_sheet_file_name:
    :return:
    """
    # 步骤1， 读取资产负债表数据
    balance_df = pd.read_csv(balance_sheet_file_name, encoding='gbk', header=0, index_col=0)
    # 第一列index有可能在excel处理后有空格，需要去除掉，否则在合并dataframe会报错
    balance_df.rename(index=lambda x: x.strip(), inplace=True)
    if balance_df.index.name == 'Verified':
        asset_and_cap_df = read_field_file(BALANCE_SHEET_FIELD_FILENAME, ['bal_order', 'ass_cap_order'])
        asset_and_cap_df = asset_and_cap_df[asset_and_cap_df['ass_cap_order']!=32767]
        asset_and_cap_df.sort_values(by='ass_cap_order', ascending=True, inplace=True)

        clist = list(balance_df.columns[1:])
        asset_and_cap_df[clist] = balance_df[clist]
        asset_and_cap_df.drop(columns=['bal_order', 'ass_cap_order'], inplace=True)

        # 计算小计、合计值
        asset_and_cap_df = asset_cap_sum_verify(asset_and_cap_df)

        return asset_and_cap_df
    else:
        print('balance sheet verification is failed.')
        return False


def safe_convert_to_float(value):
    try:
        return float(value)
    except ValueError:
        # print(f"无法转换'{value}'为浮点数。")
        return 0


def asset_cap_sum_verify(df):
    df.index.name = 'Verified'
    prefix = ''
    for col in df.columns[1:]:
        ss = df[col].apply(safe_convert_to_float)
        ss.fillna(0, inplace=True)
        ss.sum_fin_asset = (
            ss.money_cap +
            ss.trad_asset +
            ss.hfs_assets +
            ss.nca_within_1y +
            ss.oth_illiq_fin_assets +
            ss.decr_in_disbur +
            ss.oth_eq_invest +
            ss.fa_avail_for_sale +
            ss.htm_invest +
            ss.invest_real_estate +
            ss.div_receiv +
            ss.pur_resale_fa +
            ss.int_receiv
        )

        ss.sum_circle_asset = (
            ss.notes_receiv +
            ss.accounts_receiv +
            ss.receiv_financing +
            ss.prepayment +
            ss.oth_receiv +
            ss.inventories +
            ss.oth_cur_assets +
            ss.lt_rec +
            ss.use_right_assets
        )

        ss.sum_circle_debt = (
            ss.notes_payable +
            ss.payables +
            ss.acct_payable +
            ss.contract_liab +
            ss.adv_receipts +
            ss.comm_payable +
            ss.payroll_payable +
            ss.taxes_payable +
            ss.oth_payable +
            ss.lt_payroll_payable +
            ss.estimated_liab +
            ss.deferred_inc +
            ss.defer_inc_non_cur_liab +
            ss.specific_payables +
            ss.oth_cur_liab +
            ss.oth_ncl +
            ss.lease_liab
        )

        ss.sum_net_circle_asset = ss.sum_circle_asset - ss.sum_circle_debt

        ss.sum_long_asset = (
            ss.fix_assets +
            ss.cip +
            ss.const_materials +
            ss.fixed_assets_disp +
            ss.produc_bio_assets +
            ss.oil_and_gas_assets +
            ss.intan_assets +
            ss.r_and_d +
            ss.goodwill +
            ss.lt_amor_exp +
            ss.defer_tax_assets -
            ss.defer_tax_liab +
            ss.oth_nca
        )

        ss.sum_opt_asset = ss.sum_long_asset + ss.sum_net_circle_asset

        ss.sum_asset = ss.sum_opt_asset + ss.sum_fin_asset + ss.lt_eqt_invest

        ss.sum_short_debt = (
            ss.st_borr +
            ss.int_payable +
            ss.trading_fl +
            ss.hfs_sales +
            ss.non_cur_liab_due_1y +
            ss.st_bonds_payable
        )

        ss.sum_long_debt= (
            ss.lt_borr +
            ss.bond_payable +
            ss.long_pay_total
        )

        ss. sum_has_int_debt = ss.sum_long_debt + ss.sum_short_debt

        ss.sum_cap = (
            ss.sum_has_int_debt +
            ss.minority_int +
            ss.total_share +
            ss.oth_eqt_tools +
            ss.oth_eqt_tools_p_shr +
            ss.cap_rese -
            ss.treasury_share +
            ss.oth_comp_income +
            ss.special_rese +
            ss.surplus_rese +
            ss.ordin_risk_reser +
            ss.undistr_porfit +
            ss.div_payable +
            ss.forex_differ +
            ss.invest_loss_unconf
        )

        #数据校验
        verification = abs(ss.sum_cap - ss.sum_asset)
        if  verification > 10:
            print(round(verification, 0))
            prefix = 'ad' + col + prefix
        df[col] = ss
    if prefix != '':
        df.index.name = prefix
    return df

