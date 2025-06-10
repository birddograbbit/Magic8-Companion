#!/usr/bin/env python3
"""
Magic8 Trading System - Unified Test Runner
A single interface for all testing needs
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

class Colors:
    """Terminal colors for output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

class Magic8TestRunner:
    """Unified test runner for Magic8 trading system"""
    
    def __init__(self):
        self.project_root = Path("/Users/jt/magic8")
        self.magic8_path = self.project_root / "Magic8-Companion"
        self.discord_path = self.project_root / "DiscordTrading"
        
    def check_environment(self):
        """Check if the environment is properly set up"""
        print_header("Environment Check")
        
        issues = []
        
        # Check directories exist
        if not self.magic8_path.exists():
            issues.append("Magic8-Companion directory not found")
        if not self.discord_path.exists():
            issues.append("DiscordTrading directory not found")
            
        # Check for .env files
        magic8_env = self.magic8_path / ".env"
        discord_env = self.discord_path / ".env"
        
        if not magic8_env.exists():
            issues.append("Magic8-Companion/.env not found")
        if not discord_env.exists():
            issues.append("DiscordTrading/.env not found")
            
        # Check for recommendations.json
        rec_file = self.magic8_path / "data" / "recommendations.json"
        if rec_file.exists():
            print_info(f"Recommendations file found: {rec_file}")
            # Show age of recommendations
            with open(rec_file, 'r') as f:
                data = json.load(f)
                timestamp = data.get('timestamp', 'Unknown')
                print_info(f"Last recommendation: {timestamp}")
        
        if issues:
            for issue in issues:
                print_error(issue)
            return False
        else:
            print_success("Environment check passed")
            return True
    
    def test_magic8_quick(self):
        """Run quick Magic8-Companion test"""
        print_header("Magic8-Companion Quick Test")
        
        test_script = self.magic8_path / "tests" / "test_simplified.py"
        if not test_script.exists():
            # Try root directory
            test_script = self.magic8_path / "test_simplified.py"
            
        if not test_script.exists():
            print_error("test_simplified.py not found")
            return False
            
        try:
            # Change to Magic8-Companion directory
            os.chdir(self.magic8_path)
            
            # Run the test
            result = subprocess.run([sys.executable, str(test_script)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print_success("Quick test passed")
                print(result.stdout)
                return True
            else:
                print_error("Quick test failed")
                print(result.stderr)
                return False
                
        except Exception as e:
            print_error(f"Error running quick test: {e}")
            return False
    
    def test_magic8_live(self):
        """Run Magic8-Companion live data test"""
        print_header("Magic8-Companion Live Data Test")
        
        test_script = self.magic8_path / "tests" / "test_live_data.py"
        if not test_script.exists():
            # Try root directory
            test_script = self.magic8_path / "test_live_data.py"
            
        if not test_script.exists():
            print_error("test_live_data.py not found")
            return False
            
        try:
            # Change to Magic8-Companion directory
            os.chdir(self.magic8_path)
            
            print_info("Running live data test (this may take a moment)...")
            
            # Run the test
            result = subprocess.run([sys.executable, str(test_script)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print_success("Live data test passed")
                print(result.stdout)
                return True
            else:
                print_error("Live data test failed")
                print(result.stderr)
                return False
                
        except Exception as e:
            print_error(f"Error running live data test: {e}")
            return False
    
    def test_integration(self):
        """Test Magic8-DiscordTrading integration"""
        print_header("Integration Test")
        
        test_script = self.discord_path / "test_integration.py"
        if not test_script.exists():
            print_error("test_integration.py not found")
            return False
            
        try:
            # Change to DiscordTrading directory
            os.chdir(self.discord_path)
            
            # Run the test
            result = subprocess.run([sys.executable, str(test_script)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print_success("Integration test passed")
                print(result.stdout)
                return True
            else:
                print_error("Integration test failed")
                print(result.stderr)
                return False
                
        except Exception as e:
            print_error(f"Error running integration test: {e}")
            return False
    
    def monitor_live(self):
        """Monitor live integration between systems"""
        print_header("Live System Monitor")
        
        print_info("Monitoring Magic8-DiscordTrading integration...")
        print_info("Press Ctrl+C to stop monitoring\n")
        
        rec_file = self.magic8_path / "data" / "recommendations.json"
        last_modified = None
        
        try:
            while True:
                # Check if recommendations file exists
                if rec_file.exists():
                    current_modified = os.path.getmtime(rec_file)
                    
                    if last_modified is None or current_modified != last_modified:
                        last_modified = current_modified
                        
                        # Read and display recommendations
                        with open(rec_file, 'r') as f:
                            data = json.load(f)
                        
                        timestamp = data.get('timestamp', 'Unknown')
                        checkpoint = data.get('checkpoint_time', 'Unknown')
                        recommendations = data.get('recommendations', {})
                        
                        print(f"\n{Colors.BOLD}📊 Recommendation Update{Colors.ENDC}")
                        print(f"Timestamp: {timestamp}")
                        print(f"Checkpoint: {checkpoint}")
                        
                        for symbol, rec_data in recommendations.items():
                            print(f"\n{Colors.BOLD}{symbol}:{Colors.ENDC}")
                            
                            # Handle new multi-strategy format
                            strategies = rec_data.get('strategies', {})
                            best_strategy = rec_data.get('best_strategy', 'Unknown')
                            
                            if strategies:
                                # New format with multiple strategies
                                print(f"  Best Strategy: {best_strategy}")
                                for strategy, details in strategies.items():
                                    confidence = details.get('confidence', 'Unknown')
                                    score = details.get('score', 0)
                                    should_trade = details.get('should_trade', False)
                                    
                                    # Color code by confidence
                                    if confidence == 'HIGH' and should_trade:
                                        color = Colors.GREEN
                                        status = "✅ WILL TRADE"
                                    elif confidence == 'HIGH':
                                        color = Colors.GREEN
                                        status = "⚠️  HIGH but below threshold"
                                    elif confidence == 'MEDIUM':
                                        color = Colors.YELLOW
                                        status = "⚠️  SKIP (Not HIGH)"
                                    else:
                                        color = Colors.RED
                                        status = "❌ SKIP (Low confidence)"
                                    
                                    print(f"  {strategy}:")
                                    print(f"    Score: {score}")
                                    print(f"    {color}Confidence: {confidence} - {status}{Colors.ENDC}")
                            else:
                                # Old format fallback
                                confidence = rec_data.get('confidence', 'Unknown')
                                strategy = rec_data.get('preferred_strategy', 'Unknown')
                                score = rec_data.get('score', 0)
                                
                                # Color code by confidence
                                if confidence == 'HIGH':
                                    color = Colors.GREEN
                                    status = "✅ WILL TRADE"
                                elif confidence == 'MEDIUM':
                                    color = Colors.YELLOW
                                    status = "⚠️  SKIP (Not HIGH)"
                                else:
                                    color = Colors.RED
                                    status = "❌ SKIP (Low confidence)"
                                
                                print(f"  Strategy: {strategy}")
                                print(f"  Score: {score}")
                                print(f"  {color}Confidence: {confidence} - {status}{Colors.ENDC}")
                
                # Check every 5 seconds
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print_header("Running All Tests")
        
        results = {
            "Environment": self.check_environment(),
            "Magic8 Quick Test": self.test_magic8_quick(),
            "Magic8 Live Data": self.test_magic8_live(),
            "Integration": self.test_integration()
        }
        
        print_header("Test Summary")
        all_passed = True
        for test_name, passed in results.items():
            if passed:
                print_success(f"{test_name}")
            else:
                print_error(f"{test_name}")
                all_passed = False
        
        return all_passed

def main():
    """Main menu for test runner"""
    runner = Magic8TestRunner()
    
    print(f"{Colors.BOLD}")
    print("=" * 50)
    print("Magic8 Trading System - Test Runner")
    print("=" * 50)
    print(f"{Colors.ENDC}")
    
    while True:
        print("\nSelect an option:")
        print("1. Environment Check")
        print("2. Magic8-Companion Quick Test")
        print("3. Magic8-Companion Live Data Test")
        print("4. Integration Test")
        print("5. Monitor Live System")
        print("6. Run All Tests")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == '0':
            print("Goodbye!")
            break
        elif choice == '1':
            runner.check_environment()
        elif choice == '2':
            runner.test_magic8_quick()
        elif choice == '3':
            runner.test_magic8_live()
        elif choice == '4':
            runner.test_integration()
        elif choice == '5':
            runner.monitor_live()
        elif choice == '6':
            runner.run_all_tests()
        else:
            print_error("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
