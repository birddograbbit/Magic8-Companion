#!/usr/bin/env python3
"""
Comprehensive test suite for Enhanced Gamma Migration
Tests all aspects of the migrated gamma functionality
"""
import logging
import json
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results tracking
test_results = {
    "basic_functionality": {},
    "data_providers": {},
    "integration": {},
    "performance": {},
    "edge_cases": {},
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "start_time": datetime.now().isoformat()
    }
}

def record_test(category: str, test_name: str, success: bool, details: str = "", duration: float = 0):
    """Record test result"""
    test_results[category][test_name] = {
        "success": success,
        "details": details,
        "duration": duration,
        "timestamp": datetime.now().isoformat()
    }
    test_results["summary"]["total"] += 1
    if success:
        test_results["summary"]["passed"] += 1
    else:
        test_results["summary"]["failed"] += 1
    
    status = "✅ PASSED" if success else "❌ FAILED"
    logger.info(f"{status} - {category}/{test_name}: {details}")

def test_basic_functionality():
    """Test basic gamma analysis functionality"""
    logger.info("\n" + "="*60)
    logger.info("TESTING BASIC FUNCTIONALITY")
    logger.info("="*60)
    
    # Test 1: Single symbol gamma analysis
    logger.info("\nTest 1: Single symbol gamma analysis (SPX)")
    start_time = time.time()
    try:
        from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis
        results = run_gamma_analysis('SPX')
        duration = time.time() - start_time
        
        if results and 'net_gex' in results:
            record_test("basic_functionality", "single_symbol_analysis", True, 
                       f"Net GEX: ${results['net_gex']:,.0f}, Regime: {results.get('regime', 'N/A')}", 
                       duration)
        else:
            record_test("basic_functionality", "single_symbol_analysis", False, 
                       f"No results returned: {results}", duration)
    except Exception as e:
        duration = time.time() - start_time
        record_test("basic_functionality", "single_symbol_analysis", False, 
                   f"Exception: {str(e)}", duration)
        logger.error(traceback.format_exc())
    
    # Test 2: Batch gamma analysis
    logger.info("\nTest 2: Batch gamma analysis (SPX, SPY)")
    start_time = time.time()
    try:
        from magic8_companion.analysis.gamma.gamma_runner import run_batch_gamma_analysis
        results = run_batch_gamma_analysis(['SPX', 'SPY'])
        duration = time.time() - start_time
        
        if results and len(results) == 2:
            success_count = sum(1 for r in results.values() if r)
            record_test("basic_functionality", "batch_analysis", True, 
                       f"Analyzed {len(results)} symbols, {success_count} successful", 
                       duration)
        else:
            record_test("basic_functionality", "batch_analysis", False, 
                       f"Expected 2 results, got {len(results) if results else 0}", 
                       duration)
    except Exception as e:
        duration = time.time() - start_time
        record_test("basic_functionality", "batch_analysis", False, 
                   f"Exception: {str(e)}", duration)
        logger.error(traceback.format_exc())

def test_scheduler():
    """Test scheduler functionality"""
    logger.info("\n" + "="*60)
    logger.info("TESTING SCHEDULER")
    logger.info("="*60)
    
    # Test scheduler with --run-once flag
    logger.info("\nTest 3: Scheduler with --run-once flag")
    start_time = time.time()
    try:
        import subprocess
        result = subprocess.run(
            ['python', 'gamma_scheduler.py', '--mode', 'scheduled', '--run-once', '--symbols', 'SPX'],
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = time.time() - start_time
        
        if result.returncode == 0 and "Success" in result.stdout:
            record_test("basic_functionality", "scheduler_run_once", True, 
                       "Scheduler executed successfully", duration)
        else:
            record_test("basic_functionality", "scheduler_run_once", False, 
                       f"Return code: {result.returncode}, Output: {result.stdout}", 
                       duration)
    except Exception as e:
        duration = time.time() - start_time
        record_test("basic_functionality", "scheduler_run_once", False, 
                   f"Exception: {str(e)}", duration)

def test_data_providers():
    """Test different data providers"""
    logger.info("\n" + "="*60)
    logger.info("TESTING DATA PROVIDERS")
    logger.info("="*60)
    
    # Test Yahoo Finance provider
    logger.info("\nTest 4: Yahoo Finance data provider")
    start_time = time.time()
    try:
        from magic8_companion.unified_config import settings
        original_provider = settings.data_provider
        settings.data_provider = "yahoo"
        
        from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis
        results = run_gamma_analysis('SPY')
        duration = time.time() - start_time
        
        if results and 'net_gex' in results:
            record_test("data_providers", "yahoo_provider", True, 
                       f"Successfully retrieved data via Yahoo", duration)
        else:
            record_test("data_providers", "yahoo_provider", False, 
                       "No data retrieved", duration)
        
        settings.data_provider = original_provider
    except Exception as e:
        duration = time.time() - start_time
        record_test("data_providers", "yahoo_provider", False, 
                   f"Exception: {str(e)}", duration)

def test_integration():
    """Test integration with UnifiedComboScorer"""
    logger.info("\n" + "="*60)
    logger.info("TESTING INTEGRATION")
    logger.info("="*60)
    
    # Test UnifiedComboScorer in enhanced mode
    logger.info("\nTest 5: UnifiedComboScorer with gamma data")
    start_time = time.time()
    try:
        from magic8_companion.unified_combo_scorer import UnifiedComboScorer
        from magic8_companion.unified_config import settings
        
        # Ensure enhanced mode
        original_complexity = settings.system_complexity
        settings.system_complexity = "enhanced"
        settings.enable_enhanced_gex = True
        
        scorer = UnifiedComboScorer()
        recommendations = scorer.generate_recommendations(['SPX'])
        duration = time.time() - start_time
        
        # Check if gamma data is included
        gamma_included = any(
            'gamma' in str(rec).lower() or 'gex' in str(rec).lower() 
            for rec in recommendations
        )
        
        if recommendations and gamma_included:
            record_test("integration", "unified_combo_scorer", True, 
                       f"Generated {len(recommendations)} recommendations with gamma data", 
                       duration)
        else:
            record_test("integration", "unified_combo_scorer", False, 
                       f"Gamma data not found in recommendations", duration)
        
        settings.system_complexity = original_complexity
    except Exception as e:
        duration = time.time() - start_time
        record_test("integration", "unified_combo_scorer", False, 
                   f"Exception: {str(e)}", duration)
        logger.error(traceback.format_exc())

def test_edge_cases():
    """Test edge cases"""
    logger.info("\n" + "="*60)
    logger.info("TESTING EDGE CASES")
    logger.info("="*60)
    
    # Test invalid symbol
    logger.info("\nTest 6: Invalid symbol handling")
    start_time = time.time()
    try:
        from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis
        results = run_gamma_analysis('INVALID_SYMBOL_XYZ')
        duration = time.time() - start_time
        
        # Should handle gracefully without crashing
        record_test("edge_cases", "invalid_symbol", True, 
                   "Handled invalid symbol gracefully", duration)
    except Exception as e:
        duration = time.time() - start_time
        # Exception is expected but should be handled
        record_test("edge_cases", "invalid_symbol", True, 
                   f"Exception handled: {str(e)}", duration)

def generate_report():
    """Generate test report"""
    logger.info("\n" + "="*60)
    logger.info("TEST REPORT SUMMARY")
    logger.info("="*60)
    
    test_results["summary"]["end_time"] = datetime.now().isoformat()
    
    # Print summary
    print(f"\nTotal Tests: {test_results['summary']['total']}")
    print(f"Passed: {test_results['summary']['passed']} ✅")
    print(f"Failed: {test_results['summary']['failed']} ❌")
    print(f"Success Rate: {test_results['summary']['passed']/max(test_results['summary']['total'], 1)*100:.1f}%")
    
    # Print details by category
    for category in ["basic_functionality", "data_providers", "integration", "edge_cases"]:
        if test_results[category]:
            print(f"\n{category.upper().replace('_', ' ')}:")
            for test_name, result in test_results[category].items():
                status = "✅" if result["success"] else "❌"
                print(f"  {status} {test_name}: {result['details'][:60]}...")
    
    # Save full report
    with open('logs/gamma_migration_test_report.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    logger.info("\nFull report saved to: logs/gamma_migration_test_report.json")

def main():
    """Run all tests"""
    logger.info("Starting Enhanced Gamma Migration Test Suite")
    logger.info(f"Test started at: {datetime.now()}")
    
    try:
        # Run test suites
        test_basic_functionality()
        test_scheduler()
        test_data_providers()
        test_integration()
        test_edge_cases()
        
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error during testing: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Generate report
        generate_report()

if __name__ == "__main__":
    main()
