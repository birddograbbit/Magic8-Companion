# RuntimeWarning Fix

## Issue
When running `python -m magic8_companion.main`, a RuntimeWarning appears:
```
RuntimeWarning: 'magic8_companion.main' found in sys.modules after import of package 'magic8_companion', but prior to execution of 'magic8_companion.main'; this may result in unpredictable behaviour
```

## Root Cause
The `__init__.py` file was importing `main` from `.main`, causing the module to be imported before execution when using the `-m` flag.

## Solution Applied
1. Created `__main__.py` file in the package for proper module execution
2. Removed the `from .main import main` import from `__init__.py`
3. Updated package to use standard Python module execution pattern

## New Usage
Instead of:
```bash
python -m magic8_companion.main
```

Use:
```bash
python -m magic8_companion
```

Or continue using the direct script execution:
```bash
python magic8_companion/main.py
```

## Benefits
- No more RuntimeWarning
- Cleaner package structure
- Standard Python module execution pattern
- Both execution methods work without warnings

## Testing
```bash
# Test the new module execution
cd /Users/jt/magic8/Magic8-Companion
python -m magic8_companion

# Or test direct execution
python magic8_companion/main.py
```

Both methods should run without warnings.
