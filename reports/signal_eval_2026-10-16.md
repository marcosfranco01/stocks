# Divergence signal evaluation (2026-10-16)

- Data: 2019-02-09 to 2026-10-15; no skew data (IV only)
- Universe: 105 stocks (ETFs excluded). Out-of-sample from 2023-01-01.
- Entry next day's open; cost 10 bps per side per leg.
- IC = daily rank correlation of signal vs forward return. t-stats use non-overlapping periods.
- Survivorship bias: universe is today's large caps, so absolute returns are optimistic; the long-short spread is less affected.

## divergence (options_bull - price_trend)

|   horizon_days | period        |   dates |   mean_IC |    IC_t |   hit_rate_IC>0 |   top_minus_bottom_net_% |   spread_t |   annualized_spread_net_% |
|---------------:|:--------------|--------:|----------:|--------:|----------------:|-------------------------:|-----------:|--------------------------:|
|              5 | in-sample     |     747 |   -0.0171 | -1.4236 |          0.4592 |                  -0.5227 |    -1.9666 |                  -26.3459 |
|              5 | out-of-sample |     922 |   -0.0013 | -0.5632 |          0.4957 |                  -0.4971 |    -3.3346 |                  -25.0530 |
|             10 | in-sample     |     747 |   -0.0133 | -0.8686 |          0.4752 |                  -0.6349 |    -1.6338 |                  -15.9993 |
|             10 | out-of-sample |     917 |   -0.0019 |  0.5349 |          0.4875 |                  -0.5043 |    -1.1198 |                  -12.7095 |
|             20 | in-sample     |     747 |   -0.0032 | -0.1563 |          0.4685 |                  -0.6349 |    -0.1388 |                   -8.0003 |
|             20 | out-of-sample |     907 |   -0.0077 |  0.5959 |          0.4774 |                  -0.6410 |    -0.2052 |                   -8.0762 |

## options_bull only

|   horizon_days | period        |   dates |   mean_IC |    IC_t |   hit_rate_IC>0 |   top_minus_bottom_net_% |   spread_t |   annualized_spread_net_% |
|---------------:|:--------------|--------:|----------:|--------:|----------------:|-------------------------:|-----------:|--------------------------:|
|              5 | in-sample     |     747 |    0.0011 | -0.8921 |          0.4806 |                  -0.3613 |    -2.5806 |                  -18.2071 |
|              5 | out-of-sample |     922 |   -0.0003 | -0.6729 |          0.4924 |                  -0.4313 |    -3.3674 |                  -21.7385 |
|             10 | in-sample     |     747 |    0.0078 | -0.4200 |          0.5207 |                  -0.2201 |    -1.6623 |                   -5.5470 |
|             10 | out-of-sample |     917 |   -0.0029 | -0.3509 |          0.4787 |                  -0.4803 |    -1.6731 |                  -12.1026 |
|             20 | in-sample     |     747 |    0.0064 | -0.8567 |          0.5221 |                  -0.2903 |    -0.8966 |                   -3.6580 |
|             20 | out-of-sample |     907 |   -0.0016 |  0.6940 |          0.5127 |                  -0.5624 |    -0.2340 |                   -7.0859 |

## -price_trend only (short-term reversal)

|   horizon_days | period        |   dates |   mean_IC |    IC_t |   hit_rate_IC>0 |   top_minus_bottom_net_% |   spread_t |   annualized_spread_net_% |
|---------------:|:--------------|--------:|----------:|--------:|----------------:|-------------------------:|-----------:|--------------------------:|
|              5 | in-sample     |     981 |   -0.0154 | -1.0574 |          0.4424 |                  -0.5749 |    -2.7282 |                  -28.9733 |
|              5 | out-of-sample |     945 |    0.0004 |  0.2904 |          0.4783 |                  -0.4196 |    -1.9155 |                  -21.1498 |
|             10 | in-sample     |     981 |   -0.0135 | -0.7587 |          0.4567 |                  -0.8032 |    -2.4222 |                  -20.2406 |
|             10 | out-of-sample |     940 |   -0.0043 |  0.3872 |          0.4840 |                  -0.5516 |    -0.6302 |                  -13.8997 |
|             20 | in-sample     |     981 |   -0.0008 |  0.2014 |          0.4934 |                  -0.7182 |    -0.6636 |                   -9.0496 |
|             20 | out-of-sample |     930 |   -0.0190 |  0.0791 |          0.4527 |                  -0.8873 |     0.0586 |                  -11.1804 |

## -iv_change only

|   horizon_days | period        |   dates |   mean_IC |    IC_t |   hit_rate_IC>0 |   top_minus_bottom_net_% |   spread_t |   annualized_spread_net_% |
|---------------:|:--------------|--------:|----------:|--------:|----------------:|-------------------------:|-----------:|--------------------------:|
|              5 | in-sample     |     747 |    0.0011 | -0.8928 |          0.4806 |                  -0.3613 |    -2.5806 |                  -18.2071 |
|              5 | out-of-sample |     922 |   -0.0004 | -0.6743 |          0.4935 |                  -0.4313 |    -3.3674 |                  -21.7385 |
|             10 | in-sample     |     747 |    0.0078 | -0.4203 |          0.5207 |                  -0.2201 |    -1.6623 |                   -5.5470 |
|             10 | out-of-sample |     917 |   -0.0029 | -0.3519 |          0.4776 |                  -0.4803 |    -1.6731 |                  -12.1026 |
|             20 | in-sample     |     747 |    0.0064 | -0.8569 |          0.5221 |                  -0.2903 |    -0.8966 |                   -3.6580 |
|             20 | out-of-sample |     907 |   -0.0016 |  0.6927 |          0.5138 |                  -0.5624 |    -0.2340 |                   -7.0859 |

> Hypothetical research results. Not investment advice.
