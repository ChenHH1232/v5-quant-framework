# Metric Definitions

Returns are daily simple returns on common dates. Volatility is sample daily standard deviation times sqrt(252). Sharpe and information ratio use zero risk-free rate. Beta is daily covariance divided by benchmark variance. Alpha is `252 * mean(strategy - beta * benchmark)`. A benchmark with fewer than 60 common days or less than 95% coverage does not receive formal risk statistics.
