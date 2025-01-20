import selenium
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import interp1d
from datetime import datetime, timedelta

def get_coin_data(coin, date_click = 0):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(f"https://www.binance.com/en/eoptions/{coin}USDT")
    time.sleep(2)
    
    buttons = driver.find_elements(By.XPATH, '//*[contains(@class, "bn-tab bn-tab__primary data-size-small")]')
    buttons[3 + date_click].click()
    
    time.sleep(1)
    calls = driver.find_elements(By.XPATH, '//*[contains(@class, "call-row")]')
    strikes = driver.find_elements(By.XPATH, '//*[contains(@class, "t-subtitle2 !leading-[14px] text-PrimaryText")]')
    
    calls_text = [x.text for x in calls]
    strikes_text = [x.text for x in strikes]
    
    fairs_list = [float(x.split('\n')[5].replace(',','')) for x in calls_text]
    strikes_list = []
    for strike in strikes_text:
        if '\n' in strike:
            strike = strike.split('\n')[1]
        strikes_list.append(float(strike.replace(',', '')))

    assert len(fairs_list) == len(strikes_list)
    overall_list = []
    
    for i in range(len(fairs_list)):
        overall_list.append((fairs_list[i], strikes_list[i]))

    buttons = driver.find_elements(By.XPATH, '//*[contains(@class, "bn-tab bn-tab__primary data-size-small")]')
    buttons[3].click()
    time.sleep(1)

    elements = driver.find_elements(By.XPATH, '//*[contains(@class, "t-caption3 text-SecondaryText")]')
    price = float(elements[0].text.split('\n')[1][2:].replace(',', ''))
    time_left = elements[3].text.split('\n')[1][2:-7].split(':')
    
    info = {'price':price, 'time_left':(int(time_left[0]), int(time_left[1]), int(time_left[2]))}
    driver.close()
    return overall_list, info

def time_until(hour):
    now = datetime.now()
    target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now >= target_time:
        target_time += timedelta(days=1)
    return target_time - now

def probability_above_strike(c, strikes, density):
    if c < strikes[0]:
        return 100_000
    elif c > strikes[-1]:
        return 0.0
    else:
        interpolated_density = np.interp(c, strikes, density)
        extended_strikes = np.insert(strikes, np.searchsorted(strikes, c), c)
        extended_density = np.insert(density, np.searchsorted(strikes, c), interpolated_density)
        mask = extended_strikes >= c
        prob = np.trapezoid(extended_density[mask], extended_strikes[mask])
        return prob


def calculate_fair(strikes, coin, expiry, curr_px = None, date_click = 0):
    data, info = get_coin_data(coin, date_click)

    time_until_expiry = time_until(expiry)
    time_until_3am = time_until(3)
    
    const_threshold = (time_until_3am.seconds + 86400 * date_click)/time_until_expiry.seconds

    call_prices, strike_prices = zip(*data)

    if curr_px is None:
        curr_px = info['price']

    transformed_strike_prices = []
    for px in strike_prices:
        px = curr_px + (px - info['price'])/np.sqrt(const_threshold)
        transformed_strike_prices.append(float(px))

    second_derivative = np.gradient(np.gradient(call_prices, transformed_strike_prices), transformed_strike_prices)
    scaled_sigma = 1
    smoothed_second_derivative = gaussian_filter1d(second_derivative, sigma=scaled_sigma)
    
    risk_neutral_density = smoothed_second_derivative
    ans = {}
    for strike in strikes:
        prob_above_strike = probability_above_strike(strike, np.array(transformed_strike_prices), risk_neutral_density)
        min_prob = probability_above_strike(min(transformed_strike_prices), np.array(transformed_strike_prices), risk_neutral_density) 
        prob_above_strike = min(prob_above_strike, min_prob)/(min_prob + 0.05)
        prob_above_strike = float(np.round(prob_above_strike, 3))
        ans[strike] = prob_above_strike
    
    return ans

def get_kalshi_px(bitcoin = False, expiry = 17):
    now = datetime.now()
    if now.hour >= expiry:
        now = now + timedelta(days=1)
    
    month_dict = ['', 'jan', 'feb' 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    name = 'bitcoin' if bitcoin else 'ethereum'
    symbol = 'btc' if bitcoin else 'eth'
    url = f'https://kalshi.com/markets/kx{symbol}d/{name}-price-abovebelow#kx{symbol}d-{now.year%100}{month_dict[now.month]}{now.day}17'
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(3)

    elements = driver.find_elements(By.XPATH, '//*[contains(@class, "ticker-digit")]')

    num = ''
    for ele in elements:
        if ele.text == '':
            continue
        num += ele.text

    num = int(num[0:-2])/100
    driver.close()
    return num
    