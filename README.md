# kalshi_crypto

This is a simple implementation of a basic crypto options trading strategy in Kalshi. The summary of this strategy is we market take on daily 5 pm expiry options for BTC and ETH using web-scraped data from Binance, a crypto platform that provides options data as well. 

The project is organized as the following. On web-scraping side, we scrape options data from Binance to get up-to-date BTC and ETH daily options data. From there, we extrapolate the market implied distribution (using numerical tools) and time-scale to Kalshi (since daily options expire at 3 am EST for Binance and 5 pm EST for Kalshi). On the trader side, we constantly check the markets on Kalshi for when the fair values deviate from the Binance options implied distribution. We run 2 script in parallel to increase the speed of crypto trading bot. We then trade according to these signals.

