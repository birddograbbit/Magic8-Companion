#!/usr/bin/env python3
"""
SPX-Gamma-Exposure Integration Setup Script
Downloads and integrates jensolson/SPX-Gamma-Exposure functionality

This script handles the manual integration since the repository
is not a proper Python package.
"""

import os
import requests
import subprocess
from pathlib import Path

def download_spx_gex_files():
    """Download necessary files from SPX-Gamma-Exposure repository"""
    
    base_url = "https://raw.githubusercontent.com/jensolson/SPX-Gamma-Exposure/master"
    files_to_download = [
        "GEX.py",
        "pyVolLib.py"
    ]
    
    # Create SPX-GEX directory
    spx_dir = Path("src/external/spx_gex")
    spx_dir.mkdir(parents=True, exist_ok=True)
    
    # Download files
    for filename in files_to_download:
        url = f"{base_url}/{filename}"
        response = requests.get(url)
        
        if response.status_code == 200:
            file_path = spx_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"✅ Downloaded {filename}")
        else:
            print(f"❌ Failed to download {filename}: {response.status_code}")
    
    # Create __init__.py to make it a package
    init_file = spx_dir / "__init__.py"
    with open(init_file, 'w') as f:
        f.write('"""SPX Gamma Exposure integration package"""\n')
    
    print(f"✅ SPX-GEX integration files saved to: {spx_dir}")

def create_gex_wrapper():
    """Create a simplified wrapper for GEX functionality"""
    
    wrapper_content = '''"""
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
'''
    
    wrapper_path = Path("src/gex_analysis.py")
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    
    print(f"✅ Created GEX wrapper at: {wrapper_path}")

def main():
    """Main setup function"""
    print("🔧 Setting up SPX-Gamma-Exposure integration for Magic8-Companion...")
    
    # Download the SPX-GEX files
    download_spx_gex_files()
    
    # Create the wrapper
    create_gex_wrapper()
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Run: pip install -r requirements.txt")
    print("2. Test the integration with: python -c 'from src.gex_analysis import quick_gex_analysis; print(\"GEX integration ready!\")'")
    print("\nUsage in your code:")
    print("  from src.gex_analysis import quick_gex_analysis")
    print("  result = quick_gex_analysis('path/to/cboe_file.dat')")

if __name__ == "__main__":
    main()
