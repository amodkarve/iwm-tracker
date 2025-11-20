"""
Cycle Swing Momentum Indicator
Ported from PineScript V5 to Python

Original: Copyright (C) 2017-2024 whentotrade / Lars von Thienen
Source: Book "Decoding The Hidden Market Rhythm - Part 1: Dynamic Cycles"
Chapter 10: "Cycle Swing Indicator: Trading the swing of the dominant cycle"

Python port for IWM tracker
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def _cycle1(i: int, wave_throttle: float, cycs: int) -> float:
    """Helper function for Cycle1 calculation"""
    ret = 6.0 * wave_throttle + 1.0
    
    if i == 0:
        ret = 1.0 + wave_throttle
    elif i == 1:
        ret = 1.0 + wave_throttle * 5.0
    elif i == (cycs - 1):
        ret = 1.0 + wave_throttle
    elif i == (cycs - 2):
        ret = 1.0 + wave_throttle * 5.0
    
    return ret


def _cycle2(i: int, wave_throttle: float, cycs: int) -> float:
    """Helper function for Cycle2 calculation"""
    ret = -4.0 * wave_throttle
    
    if i == 0:
        ret = -2.0 * wave_throttle
    elif i == (cycs - 1):
        ret = 0.0
    elif i == (cycs - 2):
        ret = -2.0 * wave_throttle
    
    return ret


def _cycle3(i: int, wave_throttle: float, cycs: int) -> float:
    """Helper function for Cycle3 calculation"""
    ret = wave_throttle
    
    if i == (cycs - 1):
        ret = 0.0
    elif i == (cycs - 2):
        ret = 0.0
    
    return ret


def _iwtt_csi_processor(src: np.ndarray, cycle_count: int) -> np.ndarray:
    """
    Core CSI processor
    
    Args:
        src: Price data array (must have at least 50 values)
        cycle_count: Cycle count parameter
    
    Returns:
        Array of CSI values
    """
    n = len(src)
    csi_values = np.zeros(n)
    
    cycs = 50
    wave_throttle = float(160 * cycle_count)
    
    # Process each bar
    for bar_idx in range(n):
        if bar_idx < 49:
            # Not enough data yet
            csi_values[bar_idx] = 0.0
            continue
        
        # Initialize variables for this bar
        wtt1 = 0.0
        wtt2 = 0.0
        wtt3 = 0.0
        wtt4 = 0.0
        wtt5 = 0.0
        _wtt1 = 0.0
        _wtt2 = 0.0
        _wtt3 = 0.0
        _wtt5 = 0.0
        current_val = 0.0
        
        # Process cycles
        for i in range(cycs):
            swing = _cycle1(i, wave_throttle, cycs) - wtt4 * wtt1 - _wtt5 * _wtt2
            
            if swing == 0:
                break
            
            momentum = _cycle2(i, wave_throttle, cycs)
            _wtt1 = wtt1
            wtt1 = (momentum - wtt4 * wtt2) / swing
            
            acceleration = _cycle3(i, wave_throttle, cycs)
            _wtt2 = wtt2
            wtt2 = acceleration / swing
            
            # Get value from lookback
            lookback_idx = bar_idx - (49 - i)
            if lookback_idx >= 0:
                val_to_use = src[lookback_idx]
            else:
                val_to_use = 0.0
            
            current_val = (val_to_use - _wtt3 * _wtt5 - wtt3 * wtt4) / swing
            _wtt3 = wtt3
            wtt3 = current_val
            wtt4 = momentum - wtt5 * _wtt1
            _wtt5 = wtt5
            wtt5 = acceleration
        
        csi_values[bar_idx] = current_val
    
    return csi_values


def calculate_cycle_swing(src: pd.Series) -> Dict[str, pd.Series]:
    """
    Calculate Cycle Swing Momentum Indicator
    
    Args:
        src: Price series (typically close prices)
    
    Returns:
        Dictionary containing:
        - 'csi': Cycle Swing Indicator values
        - 'signal': Signal (-1, 0, 1) based on CSI
        - 'high_band': Upper dynamic band (if calculated)
        - 'low_band': Lower dynamic band (if calculated)
    """
    if len(src) < 50:
        logger.warning("Insufficient data for Cycle Swing Momentum (need >= 50 bars)")
        return {
            'csi': pd.Series(dtype=float),
            'signal': pd.Series(dtype=int),
            'high_band': pd.Series(dtype=float),
            'low_band': pd.Series(dtype=float)
        }
    
    # Convert to numpy array
    src_array = src.values
    
    # Calculate thrust components
    thrust1 = _iwtt_csi_processor(src_array, 1)
    thrust2 = _iwtt_csi_processor(src_array, 10)
    
    # Calculate CSI buffer
    csi_buffer = thrust1 - thrust2
    
    # Calculate dynamic bands (simplified version)
    # Using rolling window for band calculation
    cyclic_memory = 34
    leveling = 10
    
    high_band = np.zeros(len(csi_buffer))
    low_band = np.zeros(len(csi_buffer))
    
    for i in range(len(csi_buffer)):
        if i < cyclic_memory:
            high_band[i] = np.nan
            low_band[i] = np.nan
        else:
            # Get window
            window = csi_buffer[i-cyclic_memory+1:i+1]
            
            # Calculate percentile-based bands
            high_band[i] = np.percentile(window, 100 - leveling)
            low_band[i] = np.percentile(window, leveling)
    
    # Generate signals
    signal = np.where(
        csi_buffer >= high_band, 1,
        np.where(csi_buffer <= low_band, -1, 0)
    )
    
    return {
        'csi': pd.Series(csi_buffer, index=src.index),
        'signal': pd.Series(signal, index=src.index),
        'high_band': pd.Series(high_band, index=src.index),
        'low_band': pd.Series(low_band, index=src.index)
    }


def get_momentum_signal(src: pd.Series) -> int:
    """
    Get current momentum signal
    
    Args:
        src: Price series
    
    Returns:
        1 (overbought/bullish), -1 (oversold/bearish), or 0 (neutral)
    """
    result = calculate_cycle_swing(src)
    
    if result['signal'].empty:
        return 0
    
    return int(result['signal'].iloc[-1])


def get_csi_value(src: pd.Series) -> float:
    """
    Get current CSI value
    
    Args:
        src: Price series
    
    Returns:
        Current CSI value
    """
    result = calculate_cycle_swing(src)
    
    if result['csi'].empty:
        return 0.0
    
    return float(result['csi'].iloc[-1])
