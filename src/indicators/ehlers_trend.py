"""
Ehler's Instantaneous Trendline Indicator
Ported from PineScript V4 to Python

Original: Copyright (c) 2019-present, Franklin Moormann (cheatcountry)
Python port for IWM tracker
"""
import numpy as np
import pandas as pd
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)


def calculate_instantaneous_trend(src: pd.Series) -> Dict[str, pd.Series]:
    """
    Calculate Ehler's Instantaneous Trendline
    
    Args:
        src: Price series (typically hl2 = (high + low) / 2)
    
    Returns:
        Dictionary containing:
        - 'trendline': The instantaneous trendline values
        - 'smooth': Smoothed price values
        - 'signal': Trading signal (-1, 0, 1)
    """
    if len(src) < 50:
        logger.warning("Insufficient data for Ehler's Instantaneous Trend (need >= 50 bars)")
        return {
            'trendline': pd.Series(dtype=float),
            'smooth': pd.Series(dtype=float),
            'signal': pd.Series(dtype=int)
        }
    
    # Initialize arrays
    n = len(src)
    smooth = np.zeros(n)
    detrender = np.zeros(n)
    period = np.zeros(n)
    q1 = np.zeros(n)
    i1 = np.zeros(n)
    jI = np.zeros(n)
    jQ = np.zeros(n)
    i2 = np.zeros(n)
    q2 = np.zeros(n)
    re = np.zeros(n)
    im = np.zeros(n)
    smoothPeriod = np.zeros(n)
    iTrend = np.zeros(n)
    trendline = np.zeros(n)
    
    pi = 2 * np.arcsin(1)
    
    # Convert series to numpy array
    src_array = src.values
    
    for i in range(n):
        # Smooth calculation
        if i >= 3:
            smooth[i] = (
                (4 * src_array[i]) + 
                (3 * src_array[i-1]) + 
                (2 * src_array[i-2]) + 
                src_array[i-3]
            ) / 10
        else:
            smooth[i] = src_array[i]
        
        # Detrender calculation
        if i >= 6 and i >= 1:
            detrender[i] = (
                (0.0962 * smooth[i]) + 
                (0.5769 * smooth[i-2] if i >= 2 else 0) - 
                (0.5769 * smooth[i-4] if i >= 4 else 0) - 
                (0.0962 * smooth[i-6] if i >= 6 else 0)
            ) * ((0.075 * period[i-1] if i >= 1 else 0) + 0.54)
        
        # Q1 calculation
        if i >= 6:
            q1[i] = (
                (0.0962 * detrender[i]) + 
                (0.5769 * detrender[i-2] if i >= 2 else 0) - 
                (0.5769 * detrender[i-4] if i >= 4 else 0) - 
                (0.0962 * detrender[i-6] if i >= 6 else 0)
            ) * ((0.075 * period[i-1] if i >= 1 else 0) + 0.54)
        
        # I1 calculation
        if i >= 3:
            i1[i] = detrender[i-3]
        
        # jI calculation
        if i >= 6:
            jI[i] = (
                (0.0962 * i1[i]) + 
                (0.5769 * i1[i-2] if i >= 2 else 0) - 
                (0.5769 * i1[i-4] if i >= 4 else 0) - 
                (0.0962 * i1[i-6] if i >= 6 else 0)
            ) * ((0.075 * period[i-1] if i >= 1 else 0) + 0.54)
        
        # jQ calculation
        if i >= 6:
            jQ[i] = (
                (0.0962 * q1[i]) + 
                (0.5769 * q1[i-2] if i >= 2 else 0) - 
                (0.5769 * q1[i-4] if i >= 4 else 0) - 
                (0.0962 * q1[i-6] if i >= 6 else 0)
            ) * ((0.075 * period[i-1] if i >= 1 else 0) + 0.54)
        
        # I2 and Q2 calculations with smoothing
        i2_raw = i1[i] - jQ[i]
        i2[i] = (0.2 * i2_raw) + (0.8 * i2[i-1] if i >= 1 else 0)
        
        q2_raw = q1[i] + jI[i]
        q2[i] = (0.2 * q2_raw) + (0.8 * q2[i-1] if i >= 1 else 0)
        
        # Re and Im calculations with smoothing
        re_raw = (i2[i] * i2[i-1] if i >= 1 else 0) + (q2[i] * q2[i-1] if i >= 1 else 0)
        re[i] = (0.2 * re_raw) + (0.8 * re[i-1] if i >= 1 else 0)
        
        im_raw = (i2[i] * q2[i-1] if i >= 1 else 0) - (q2[i] * i2[i-1] if i >= 1 else 0)
        im[i] = (0.2 * im_raw) + (0.8 * im[i-1] if i >= 1 else 0)
        
        # Period calculation
        if im[i] != 0 and re[i] != 0:
            period[i] = 2 * pi / np.arctan(im[i] / re[i])
        else:
            period[i] = 0
        
        # Period constraints
        if i >= 1:
            period[i] = min(max(period[i], 0.67 * period[i-1]), 1.5 * period[i-1])
        period[i] = min(max(period[i], 6), 50)
        period[i] = (0.2 * period[i]) + (0.8 * period[i-1] if i >= 1 else 0)
        
        # Smooth period
        smoothPeriod[i] = (0.33 * period[i]) + (0.67 * smoothPeriod[i-1] if i >= 1 else 0)
        
        # Calculate iTrend using dcPeriod
        dcPeriod = int(np.ceil(smoothPeriod[i] + 0.5))
        iTrend_sum = 0
        for j in range(dcPeriod):
            if i >= j:
                iTrend_sum += src_array[i-j]
        
        if dcPeriod > 0:
            iTrend[i] = iTrend_sum / dcPeriod
        else:
            iTrend[i] = src_array[i]
        
        # Calculate trendline
        if i >= 3:
            trendline[i] = (
                (4 * iTrend[i]) + 
                (3 * iTrend[i-1]) + 
                (2 * iTrend[i-2]) + 
                iTrend[i-3]
            ) / 10
        else:
            trendline[i] = iTrend[i]
    
    # Calculate signal
    signal = np.where(smooth > trendline, 1, np.where(smooth < trendline, -1, 0))
    
    return {
        'trendline': pd.Series(trendline, index=src.index),
        'smooth': pd.Series(smooth, index=src.index),
        'signal': pd.Series(signal, index=src.index)
    }


def get_trend_signal(src: pd.Series) -> int:
    """
    Get current trend signal
    
    Args:
        src: Price series
    
    Returns:
        1 (bullish), -1 (bearish), or 0 (neutral)
    """
    result = calculate_instantaneous_trend(src)
    
    if result['signal'].empty:
        return 0
    
    return int(result['signal'].iloc[-1])
