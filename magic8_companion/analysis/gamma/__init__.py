"""
Gamma Analysis Module for Magic8-Companion.
Native implementation of Enhanced Gamma Exposure analysis.
"""
from .calculator import GammaExposureCalculator
from .levels import GammaLevels
from .regime import MarketRegimeAnalyzer

__all__ = [
    'GammaExposureCalculator',
    'GammaLevels',
    'MarketRegimeAnalyzer'
]

# Version info
__version__ = '1.0.0'
__author__ = 'Magic8-Companion Team'
