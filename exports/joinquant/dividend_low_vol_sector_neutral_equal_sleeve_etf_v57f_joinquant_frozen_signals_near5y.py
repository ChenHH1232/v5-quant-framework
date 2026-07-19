from jqdata import *


"""
Bank Quant V5 - Dividend Low-Vol Cash-Flow enhanced ETF frozen-signal JoinQuant script.

Purpose:
- Platform replication preparation for a frozen cross-sector basket.
- This is not an accepted strategy and must not be tuned after seeing JoinQuant results.

Frozen rule:
- Use local basket_rebalance_signals.csv exactly.
- Rebalance only on exact frozen signal dates.
- Use order_target_value, not order_target_percent, for compatibility with JoinQuant runtimes.
- No timing overlay, no stop loss, no take profit, no return tuning.

Comparison contract:
- Local runner executes at daily open and values at daily close.
- JoinQuant scheduled execution is 09:40, so small execution differences are expected.
- JoinQuant display benchmark is only a platform reference.
- Formal relative judgment should use local same-pool total-return benchmark and attribution packet.
"""


FROZEN_SIGNALS = {
    '2021-10-08': [('600969.XSHG', 0.035714285710, 'utilities_electricity'), ('000543.XSHE', 0.035714285710, 'utilities_electricity'), ('600617.XSHG', 0.035714285710, 'utilities_electricity'), ('000421.XSHE', 0.035714285710, 'utilities_electricity'), ('000539.XSHE', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601077.XSHG', 0.035714285710, 'bank'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601988.XSHG', 0.035714285710, 'bank'), ('002040.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600928.XSHG', 0.035714285710, 'bank'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601288.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('603323.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('600368.XSHG', 0.035714285710, 'highway_infrastructure'), ('601333.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600106.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2022-01-04': [('000421.XSHE', 0.035714285710, 'utilities_electricity'), ('003816.XSHE', 0.035714285710, 'utilities_electricity'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600969.XSHG', 0.035714285710, 'utilities_electricity'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('600617.XSHG', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('601368.XSHG', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('002893.XSHE', 0.035714285710, 'utilities_electricity'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601008.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601288.XSHG', 0.035714285710, 'bank'), ('600928.XSHG', 0.035714285710, 'bank'), ('601988.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('601229.XSHG', 0.035714285710, 'bank'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('002807.XSHE', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600368.XSHG', 0.035714285710, 'highway_infrastructure'), ('002040.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2022-04-01': [('000421.XSHE', 0.035714285710, 'utilities_electricity'), ('600681.XSHG', 0.035714285710, 'utilities_electricity'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('002267.XSHE', 0.035714285710, 'utilities_electricity'), ('003816.XSHE', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('600886.XSHG', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('601398.XSHG', 0.035714285710, 'bank'), ('601288.XSHG', 0.035714285710, 'bank'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601988.XSHG', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601939.XSHG', 0.035714285710, 'bank'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('601229.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601228.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000582.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2022-07-01': [('000883.XSHE', 0.035714285710, 'utilities_electricity'), ('002608.XSHE', 0.035714285710, 'utilities_electricity'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('003816.XSHE', 0.035714285710, 'utilities_electricity'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('600886.XSHG', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601288.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601825.XSHG', 0.035714285710, 'bank'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601988.XSHG', 0.035714285710, 'bank'), ('601939.XSHG', 0.035714285710, 'bank'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601000.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601169.XSHG', 0.035714285710, 'bank'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2022-10-10': [('600803.XSHG', 0.035714285710, 'utilities_electricity'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('600719.XSHG', 0.035714285710, 'utilities_electricity'), ('600008.XSHG', 0.035714285710, 'utilities_electricity'), ('000598.XSHE', 0.035714285710, 'utilities_electricity'), ('003816.XSHE', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601825.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('601288.XSHG', 0.035714285710, 'bank'), ('601939.XSHG', 0.035714285710, 'bank'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('601988.XSHG', 0.035714285710, 'bank'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601169.XSHG', 0.035714285710, 'bank'), ('601008.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2023-01-03': [('600098.XSHG', 0.035714285710, 'utilities_electricity'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('003816.XSHE', 0.035714285710, 'utilities_electricity'), ('600886.XSHG', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('002039.XSHE', 0.035714285710, 'utilities_electricity'), ('600461.XSHG', 0.035714285710, 'utilities_electricity'), ('600283.XSHG', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601825.XSHG', 0.035714285710, 'bank'), ('601939.XSHG', 0.035714285710, 'bank'), ('601288.XSHG', 0.035714285710, 'bank'), ('601997.XSHG', 0.035714285710, 'bank'), ('601988.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('000905.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601000.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2023-04-03': [('600168.XSHG', 0.035714285710, 'utilities_electricity'), ('600098.XSHG', 0.035714285710, 'utilities_electricity'), ('600681.XSHG', 0.035714285710, 'utilities_electricity'), ('600283.XSHG', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('600956.XSHG', 0.035714285710, 'utilities_electricity'), ('600617.XSHG', 0.035714285710, 'utilities_electricity'), ('601825.XSHG', 0.035714285710, 'bank'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601288.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('601939.XSHG', 0.035714285710, 'bank'), ('601988.XSHG', 0.035714285710, 'bank'), ('601169.XSHG', 0.035714285710, 'bank'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2023-07-03': [('000883.XSHE', 0.035714285710, 'utilities_electricity'), ('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('002267.XSHE', 0.035714285710, 'utilities_electricity'), ('600617.XSHG', 0.035714285710, 'utilities_electricity'), ('600642.XSHG', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000421.XSHE', 0.035714285710, 'utilities_electricity'), ('601825.XSHG', 0.035714285710, 'bank'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601228.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601077.XSHG', 0.035714285710, 'bank'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('002807.XSHE', 0.035714285710, 'bank'), ('601997.XSHG', 0.035714285710, 'bank'), ('601229.XSHG', 0.035714285710, 'bank'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600908.XSHG', 0.035714285710, 'bank'), ('603323.XSHG', 0.035714285710, 'bank'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000557.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2023-10-09': [('601985.XSHG', 0.035714285710, 'utilities_electricity'), ('003816.XSHE', 0.035714285710, 'utilities_electricity'), ('600969.XSHG', 0.035714285710, 'utilities_electricity'), ('600617.XSHG', 0.035714285710, 'utilities_electricity'), ('000421.XSHE', 0.035714285710, 'utilities_electricity'), ('000407.XSHE', 0.035714285710, 'utilities_electricity'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600396.XSHG', 0.035714285710, 'utilities_electricity'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601825.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('600908.XSHG', 0.035714285710, 'bank'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('601229.XSHG', 0.035714285710, 'bank'), ('601077.XSHG', 0.035714285710, 'bank'), ('603323.XSHG', 0.035714285710, 'bank'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601166.XSHG', 0.035714285710, 'bank'), ('000582.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('601008.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2024-01-02': [('002039.XSHE', 0.035714285710, 'utilities_electricity'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000692.XSHE', 0.035714285710, 'utilities_electricity'), ('000791.XSHE', 0.035714285710, 'utilities_electricity'), ('601825.XSHG', 0.035714285710, 'bank'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('600617.XSHG', 0.035714285710, 'utilities_electricity'), ('000905.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('601229.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601169.XSHG', 0.035714285710, 'bank'), ('603323.XSHG', 0.035714285710, 'bank'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601398.XSHG', 0.035714285710, 'bank'), ('000582.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('601228.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2024-04-01': [('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('600578.XSHG', 0.035714285710, 'utilities_electricity'), ('600803.XSHG', 0.035714285710, 'utilities_electricity'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000692.XSHE', 0.035714285710, 'utilities_electricity'), ('000690.XSHE', 0.035714285710, 'utilities_electricity'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('600886.XSHG', 0.035714285710, 'utilities_electricity'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('002807.XSHE', 0.035714285710, 'bank'), ('601077.XSHG', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601229.XSHG', 0.035714285710, 'bank'), ('603323.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('601187.XSHG', 0.035714285710, 'bank'), ('600000.XSHG', 0.035714285710, 'bank'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601816.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2024-07-01': [('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('000539.XSHE', 0.035714285710, 'utilities_electricity'), ('600021.XSHG', 0.035714285710, 'utilities_electricity'), ('000883.XSHE', 0.035714285710, 'utilities_electricity'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('600011.XSHG', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601008.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601398.XSHG', 0.035714285710, 'bank'), ('601939.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('600000.XSHG', 0.035714285710, 'bank'), ('600908.XSHG', 0.035714285710, 'bank'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601816.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601169.XSHG', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2024-10-08': [('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000539.XSHE', 0.035714285710, 'utilities_electricity'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600681.XSHG', 0.035714285710, 'utilities_electricity'), ('600021.XSHG', 0.035714285710, 'utilities_electricity'), ('600803.XSHG', 0.035714285710, 'utilities_electricity'), ('000601.XSHE', 0.035714285710, 'utilities_electricity'), ('601077.XSHG', 0.035714285710, 'bank'), ('000905.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('601818.XSHG', 0.035714285710, 'bank'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('002807.XSHE', 0.035714285710, 'bank'), ('601816.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600908.XSHG', 0.035714285710, 'bank'), ('601166.XSHG', 0.035714285710, 'bank'), ('601988.XSHG', 0.035714285710, 'bank'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601398.XSHG', 0.035714285710, 'bank'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('000828.XSHE', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2025-01-02': [('000539.XSHE', 0.035714285710, 'utilities_electricity'), ('600969.XSHG', 0.035714285710, 'utilities_electricity'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('600744.XSHG', 0.035714285710, 'utilities_electricity'), ('600098.XSHG', 0.035714285710, 'utilities_electricity'), ('002039.XSHE', 0.035714285710, 'utilities_electricity'), ('000905.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600908.XSHG', 0.035714285710, 'bank'), ('601228.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('002807.XSHE', 0.035714285710, 'bank'), ('002966.XSHE', 0.035714285710, 'bank'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('601825.XSHG', 0.035714285710, 'bank'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601818.XSHG', 0.035714285710, 'bank'), ('601528.XSHG', 0.035714285710, 'bank'), ('601997.XSHG', 0.035714285710, 'bank'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000828.XSHE', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2025-04-01': [('600098.XSHG', 0.035714285710, 'utilities_electricity'), ('002039.XSHE', 0.035714285710, 'utilities_electricity'), ('601008.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000543.XSHE', 0.035714285710, 'utilities_electricity'), ('600803.XSHG', 0.035714285710, 'utilities_electricity'), ('600578.XSHG', 0.035714285710, 'utilities_electricity'), ('000791.XSHE', 0.035714285710, 'utilities_electricity'), ('000407.XSHE', 0.035714285710, 'utilities_electricity'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('000905.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601825.XSHG', 0.035714285710, 'bank'), ('601398.XSHG', 0.035714285710, 'bank'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601997.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('600908.XSHG', 0.035714285710, 'bank'), ('601988.XSHG', 0.035714285710, 'bank'), ('002966.XSHE', 0.035714285710, 'bank'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601228.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('000828.XSHE', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2025-07-01': [('600011.XSHG', 0.035714285710, 'utilities_electricity'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('600027.XSHG', 0.035714285710, 'utilities_electricity'), ('000543.XSHE', 0.035714285710, 'utilities_electricity'), ('600021.XSHG', 0.035714285710, 'utilities_electricity'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('000900.XSHE', 0.035714285710, 'highway_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('001213.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('601398.XSHG', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601997.XSHG', 0.035714285710, 'bank'), ('601333.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601228.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600908.XSHG', 0.035714285710, 'bank'), ('002807.XSHE', 0.035714285710, 'bank'), ('601009.XSHG', 0.035714285710, 'bank'), ('000001.XSHE', 0.035714285710, 'bank'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601939.XSHG', 0.035714285710, 'bank'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('000429.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2025-10-09': [('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('000421.XSHE', 0.035714285710, 'utilities_electricity'), ('600011.XSHG', 0.035714285710, 'utilities_electricity'), ('603689.XSHG', 0.035714285710, 'utilities_electricity'), ('600027.XSHG', 0.035714285710, 'utilities_electricity'), ('600803.XSHG', 0.035714285710, 'utilities_electricity'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601139.XSHG', 0.035714285710, 'utilities_electricity'), ('600908.XSHG', 0.035714285710, 'bank'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('601528.XSHG', 0.035714285710, 'bank'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure'), ('002839.XSHE', 0.035714285710, 'bank'), ('601333.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601326.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000828.XSHE', 0.035714285710, 'highway_infrastructure'), ('002807.XSHE', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000001.XSHE', 0.035714285710, 'bank'), ('601018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601398.XSHG', 0.035714285710, 'bank'), ('601997.XSHG', 0.035714285710, 'bank'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
    '2026-01-05': [('002039.XSHE', 0.035714285710, 'utilities_electricity'), ('000543.XSHE', 0.035714285710, 'utilities_electricity'), ('600027.XSHG', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('600011.XSHG', 0.035714285710, 'utilities_electricity'), ('600795.XSHG', 0.035714285710, 'utilities_electricity'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600908.XSHG', 0.035714285710, 'bank'), ('601991.XSHG', 0.035714285710, 'utilities_electricity'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('601528.XSHG', 0.035714285710, 'bank'), ('000828.XSHE', 0.035714285710, 'highway_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('603323.XSHG', 0.035714285710, 'bank'), ('600018.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000001.XSHE', 0.035714285710, 'bank'), ('002839.XSHE', 0.035714285710, 'bank'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601000.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601997.XSHG', 0.035714285710, 'bank'), ('601298.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('601860.XSHG', 0.035714285710, 'bank'), ('000755.XSHE', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure'), ('000548.XSHE', 0.035714285710, 'highway_infrastructure')],
    '2026-04-01': [('002039.XSHE', 0.035714285710, 'utilities_electricity'), ('000027.XSHE', 0.035714285710, 'utilities_electricity'), ('600717.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('000543.XSHE', 0.035714285710, 'utilities_electricity'), ('600886.XSHG', 0.035714285710, 'utilities_electricity'), ('600023.XSHG', 0.035714285710, 'utilities_electricity'), ('600642.XSHG', 0.035714285710, 'utilities_electricity'), ('601139.XSHG', 0.035714285710, 'utilities_electricity'), ('601333.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600035.XSHG', 0.035714285710, 'highway_infrastructure'), ('600908.XSHG', 0.035714285710, 'bank'), ('001872.XSHE', 0.035714285710, 'port_rail_infrastructure'), ('600020.XSHG', 0.035714285710, 'highway_infrastructure'), ('601528.XSHG', 0.035714285710, 'bank'), ('601997.XSHG', 0.035714285710, 'bank'), ('601128.XSHG', 0.035714285710, 'bank'), ('601006.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('603323.XSHG', 0.035714285710, 'bank'), ('000001.XSHE', 0.035714285710, 'bank'), ('000828.XSHE', 0.035714285710, 'highway_infrastructure'), ('601169.XSHG', 0.035714285710, 'bank'), ('601816.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600017.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('601880.XSHG', 0.035714285710, 'port_rail_infrastructure'), ('600350.XSHG', 0.035714285710, 'highway_infrastructure'), ('600012.XSHG', 0.035714285710, 'highway_infrastructure'), ('600033.XSHG', 0.035714285710, 'highway_infrastructure'), ('600377.XSHG', 0.035714285710, 'highway_infrastructure')],
}

FIRST_SIGNAL_DATE = '2021-10-08'


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock',
    )

    g.strategy_id = 'dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f'
    g.script_version = 'v57f_etf_frozen_signals_20260719'
    g.target_exposure = 0.995000000000
    g.selection_count = 28
    g.lot_size = 100
    g.executed_dates = set()
    g.debug = True

    log.info('basket script=%s strategy=%s frozen_signal_dates=%d first_signal=%s benchmark=%s' % (
        g.script_version,
        g.strategy_id,
        len(FROZEN_SIGNALS),
        FIRST_SIGNAL_DATE,
        '000300.XSHG',
    ))
    log.info('frozen rule: exact local basket signals; no recompute, no tuning, no accepted-strategy claim.')
    log.info('benchmark note: platform benchmark is display-only; formal comparison uses local same-pool total-return benchmark.')

    run_daily(maybe_rebalance, time='09:40')
    run_daily(after_close_log, time='after_close')


def maybe_rebalance(context):
    today = context.current_dt.date().isoformat()
    if today not in FROZEN_SIGNALS:
        return
    if today in g.executed_dates:
        return

    rows = FROZEN_SIGNALS[today]
    tradable_rows = []
    for code, weight, sector_id in rows:
        if is_tradable(code):
            tradable_rows.append((code, weight, sector_id))
        else:
            log.info('skip untradable date=%s code=%s sector=%s' % (today, code, sector_id))

    if not tradable_rows:
        log.info('BLOCKED no tradable selected stocks date=%s' % today)
        g.executed_dates.add(today)
        return

    total_value = context.portfolio.total_value
    log.info(
        'rebalance date=%s raw_selected=%d tradable_selected=%d target_exposure=%.4f selected=%s'
        % (today, len(rows), len(tradable_rows), g.target_exposure, ','.join([item[0] for item in tradable_rows]))
    )
    execute_target_weights(context, tradable_rows, total_value)
    g.executed_dates.add(today)


def execute_target_weights(context, target_rows, total_value):
    selected = set([code for code, _weight, _sector in target_rows])
    current_positions = list(context.portfolio.positions.keys())
    current_data = get_current_data()

    for code in current_positions:
        if code not in selected:
            try:
                order_target_value(code, 0)
            except Exception as exc:
                log.info('sell failed code=%s error=%s' % (code, str(exc)))

    for code, weight, sector_id in target_rows:
        target_value = total_value * float(weight) * g.target_exposure
        estimated_price = get_estimated_trade_price(current_data, code)
        if estimated_price is not None:
            min_lot_value = estimated_price * g.lot_size
            if target_value < min_lot_value:
                log.info(
                    'capital warning code=%s target_value=%.2f one_lot_value=%.2f price=%.3f lot_size=%d; order may be rejected by lot-size rule.'
                    % (code, target_value, min_lot_value, estimated_price, g.lot_size)
                )
        try:
            order_target_value(code, target_value)
        except Exception as exc:
            log.info('buy/adjust failed code=%s sector=%s target_value=%.2f error=%s' % (code, sector_id, target_value, str(exc)))


def get_estimated_trade_price(current_data, code):
    try:
        item = current_data[code]
    except Exception:
        return None
    for attr in ('last_price', 'day_open', 'high_limit', 'low_limit'):
        try:
            value = getattr(item, attr, None)
        except Exception:
            value = None
        if value is not None and value > 0:
            return float(value)
    return None


def is_tradable(code):
    current_data = get_current_data()
    try:
        item = current_data[code]
    except Exception:
        return False
    if getattr(item, 'paused', False):
        return False
    if getattr(item, 'is_st', False):
        return False
    return True


def after_close_log(context):
    today = context.current_dt.date().isoformat()
    if today not in FROZEN_SIGNALS:
        return
    positions = []
    for code, pos in context.portfolio.positions.items():
        if pos.total_amount > 0:
            positions.append('%s:%s' % (code, int(pos.total_amount)))
    log.info(
        'after_close date=%s total_value=%.2f cash=%.2f positions=%s'
        % (today, context.portfolio.total_value, context.portfolio.cash, ';'.join(positions))
    )
