"""
Simplified wrapper for SPX-Gamma-Exposure functionality
Provides easy-to-use functions for Magic8-Companion
"""

import sys
from pathlib import Path

# Add the SPX-GEX directory to Python path
spx_gex_path = Path(__file__).parent / "external" / "spx_gex"
sys.path.insert(0, str(spx_gex_path))

try:
    from GEX import CBOE_GEX, CBOE_Greeks
except ImportError as e:
    print(f"Warning: Could not import SPX-GEX functions: {e}")
    print("Run: python setup_spx_gex.py to download required files")

class GammaExposureAnalyzer:
    """Simplified interface for gamma exposure analysis"""
    
    def __init__(self):
        self.last_gex_data = None
    
    def calculate_spot_gex(self, cboe_filename: str) -> float:
        """
        Calculate current spot gamma exposure
        
        Args:
            cboe_filename: Path to CBOE .dat file
            
        Returns:
            Current gamma exposure value
        """
        try:
            gex_value = CBOE_GEX(cboe_filename, sens=False, plot=False)
            self.last_gex_data = gex_value
            return gex_value
        except Exception as e:
            print(f"Error calculating GEX: {e}")
            return 0.0
    
    def get_gex_sensitivity(self, cboe_filename: str, plot: bool = False):
        """
        Get GEX sensitivity across strike range
        
        Args:
            cboe_filename: Path to CBOE .dat file
            plot: Whether to show plot
            
        Returns:
            Pandas Series with GEX by strike price
        """
        try:
            return CBOE_GEX(cboe_filename, sens=True, plot=plot)
        except Exception as e:
            print(f"Error calculating GEX sensitivity: {e}")
            return None
    
    def analyze_pinning_risk(self, cboe_filename: str) -> dict:
        """
        Analyze gamma pinning risk for combo selection
        
        Returns:
            Dictionary with pinning analysis
        """
        try:
            gex_series = self.get_gex_sensitivity(cboe_filename, plot=False)
            if gex_series is None:
                return {"error": "Could not calculate GEX"}
            
            # Find zero GEX level (pinning point)
            zero_gex = int(gex_series[gex_series.abs() == gex_series.abs().min()].index[0])
            current_gex = gex_series.iloc[-1]  # Assume last value is current spot
            
            return {
                "zero_gex_level": zero_gex,
                "current_gex": current_gex,
                "pinning_strength": abs(current_gex),
                "above_zero_gex": current_gex > 0,
                "summary": "Strong pinning" if abs(current_gex) > 100 else "Weak pinning"
            }
        except Exception as e:
            return {"error": f"Error in pinning analysis: {e}"}

# Convenience function for quick GEX calculation
def quick_gex_analysis(cboe_file: str) -> dict:
    """
    Quick gamma exposure analysis for Magic8-Companion
    
    Args:
        cboe_file: Path to CBOE data file
        
    Returns:
        Dictionary with GEX analysis results
    """
    analyzer = GammaExposureAnalyzer()
    
    # Get basic GEX value
    spot_gex = analyzer.calculate_spot_gex(cboe_file)
    
    # Get pinning analysis
    pinning_data = analyzer.analyze_pinning_risk(cboe_file)
    
    return {
        "spot_gex": spot_gex,
        "pinning_analysis": pinning_data,
        "timestamp": None  # Could add timestamp if needed
    }
