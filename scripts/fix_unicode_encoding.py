#!/usr/bin/env python3
"""
Unicode Encoding Fix Script
Finds and fixes Unicode encoding issues across the entire wildfire project
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

class UnicodeFixer:
    """Fix Unicode encoding issues in project files"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.unicode_replacements = {
            # Emojis to text replacements
            '[TROPHY]': '[TROPHY]',
            '[FIRE]': '[FIRE]',
            '[BAR_CHART]': '[CHART]',
            '[FILES]': '[FILES]',
            '[GLOBE]': '[GLOBE]',
            '[ROCKET]': '[ROCKET]',
            '[CHECK]': '[CHECK]',
            '[X]': '[X]',
            '[WARNING]': '[WARNING]',
            '[DART]': '[TARGET]',
            '[LINE_CHART]': '[TRENDING_UP]',
            '[LOCK]': '[LOCK]',
            '[KEY]': '[KEY]',
            '[LOCKED_KEY]': '[LOCKED_KEY]',
            '[DOCUMENT]': '[DOCUMENT]',
            '[BOOKS]': '[BOOKS]',
            '[MICROSCOPE]': '[MICROSCOPE]',
            '[MAP]': '[MAP]',
            '[THERMOMETER]': '[THERMOMETER]',
            '[SATELLITE]': '[SATELLITE]',
            '[ROBOT]': '[ROBOT]',
            '[LIGHTNING]': '[LIGHTNING]',
            '[PARTY]': '[PARTY]',
            '[BULB]': '[BULB]',
            '[MEMO]': '[MEMO]',
            '[MAGNIFYING_GLASS]': '[MAGNIFYING_GLASS]',
            '[PHONE]': '[PHONE]',
            '[MEDAL]': '[MEDAL]',
            '[CIRCUS_TENT]': '[CIRCUS_TENT]',
            '[STAR]': '[STAR]',
            '[MONEY_BAG]': '[MONEY_BAG]',
            '[CLIPBOARD]': '[CLIPBOARD]',
            '[PALETTE]': '[PALETTE]',
            '[STAR]': '[STAR]',
            '[LAPTOP]': '[LAPTOP]',
            '[MOBILE]': '[MOBILE]',
            '[DESKTOP]': '[DESKTOP]',
            '[PRINTER]': '[PRINTER]',
            '[SATELLITE_ANTENNA]': '[SATELLITE_ANTENNA]',
            '[WRENCH]': '[WRENCH]',
            '[GEAR]': '[GEAR]',
            '[HAMMER]': '[HAMMER]',
            '[BAR_CHART]': '[BAR_CHART]',
            '[LINE_CHART]': '[LINE_CHART]',
            '[CHART_DOWN]': '[CHART_DOWN]',
            '[PIN]': '[PIN]',
            '[LOCATION_PIN]': '[LOCATION_PIN]',
            '[GAME_CONTROLLER]': '[GAME_CONTROLLER]',
            '[DICE]': '[DICE]',
            '[DART]': '[DART]',
            '[RUNNER]': '[RUNNER]',
            '[WALKER]': '[WALKER]',
            '[CAR]': '[CAR]',
            '[SUV]': '[SUV]',
            '[MINIBUS]': '[MINIBUS]',
            '[TRUCK]': '[TRUCK]',
            '[HELICOPTER]': '[HELICOPTER]',
            '[AIRPLANE]': '[AIRPLANE]',
            '[UFO]': '[UFO]',
            '[SHIP]': '[SHIP]',
            '[SAILBOAT]': '[SAILBOAT]',
            '[HOUSE]': '[HOUSE]',
            '[OFFICE_BUILDING]': '[OFFICE_BUILDING]',
            '[FACTORY]': '[FACTORY]',
            '[CONSTRUCTION]': '[CONSTRUCTION]',
            '[TREE]': '[TREE]',
            '[EVERGREEN_TREE]': '[EVERGREEN_TREE]',
            '[PALM_TREE]': '[PALM_TREE]',
            '[SEEDLING]': '[SEEDLING]',
            '[HERB]': '[HERB]',
            '[LEAVES]': '[LEAVES]',
            '[SHEAF_OF_RICE]': '[SHEAF_OF_RICE]',
            '[FIRE]': '[FIRE]',
            '[DROPLET]': '[DROPLET]',
            '[WATER_WAVE]': '[WATER_WAVE]',
            '[SNOWFLAKE]': '[SNOWFLAKE]',
            '[SUN]': '[SUN]',
            '[SUN_CLOUD]': '[SUN_CLOUD]',
            '[PARTLY_CLOUDY]': '[PARTLY_CLOUDY]',
            '[CLOUD]': '[CLOUD]',
            '[RAIN_CLOUD]': '[RAIN_CLOUD]',
            '[STORM]': '[STORM]',
            '[LIGHTNING_CLOUD]': '[LIGHTNING_CLOUD]',
            '[SNOW_CLOUD]': '[SNOW_CLOUD]',
            '[UMBRELLA]': '[UMBRELLA]',
            '[BEACH_UMBRELLA]': '[BEACH_UMBRELLA]',

            # Unicode symbols to ASCII
            '->': '->',
            '<-': '<-',
            '^': '^',
            'v': 'v',
            '<->': '<->',
            '~=': '~=',
            '!=': '!=',
            '<=': '<=',
            '>=': '>=',
            'infinity': 'infinity',
            'deg': 'deg',
            '+/-': '+/-',
            'x': 'x',
            '/': '/',
            'sqrt': 'sqrt',
            'sum': 'sum',
            'delta': 'delta',
            'nabla': 'nabla',
            'partial': 'partial',
            'integral': 'integral',
            'product': 'product',
            'union': 'union',
            'intersection': 'intersection',
            'in': 'in',
            'not_in': 'not_in',
            'subset': 'subset',
            'superset': 'superset',
            'subset_eq': 'subset_eq',
            'superset_eq': 'superset_eq',
            'empty_set': 'empty_set',
            'for_all': 'for_all',
            'exists': 'exists',
            'not_exists': 'not_exists',
            'and': 'and',
            'or': 'or',
            'not': 'not',
            'xor': 'xor',
            'otimes': 'otimes',
            'odot': 'odot',
            'oslash': 'oslash',
            'perp': 'perp',
            'parallel': 'parallel',
            'not_parallel': 'not_parallel',
            'angle': 'angle',
            'measured_angle': 'measured_angle',
            'spherical_angle': 'spherical_angle',
            'proportional': 'proportional',
            'infinity': 'infinity',

            # Special quotes and dashes
            '"': '"',
            '"': '"',
            "'": "'",
            '--': '--',
            '...': '...',
            '*': '*',
            'o': 'o',
            '>': '>',
            '-': '-',
            '??': '??',
            '?!': '?!',
            '!?': '!?',
            '!!': '!!',

            # Mathematical symbols
            'alpha': 'alpha',
            'beta': 'beta',
            'gamma': 'gamma',
            'delta': 'delta',
            'epsilon': 'epsilon',
            'zeta': 'zeta',
            'eta': 'eta',
            'theta': 'theta',
            'iota': 'iota',
            'kappa': 'kappa',
            'lambda': 'lambda',
            'mu': 'mu',
            'nu': 'nu',
            'xi': 'xi',
            'omicron': 'omicron',
            'pi': 'pi',
            'rho': 'rho',
            'sigma': 'sigma',
            'tau': 'tau',
            'upsilon': 'upsilon',
            'phi': 'phi',
            'chi': 'chi',
            'psi': 'psi',
            'omega': 'omega',

            # Currency and symbols
            'EUR': 'EUR',
            'GBP': 'GBP',
            'JPY': 'JPY',
            'cents': 'cents',
            '(C)': '(C)',
            '(R)': '(R)',
            '(TM)': '(TM)',
            'section': 'section',
            'paragraph': 'paragraph',
            'dagger': 'dagger',
            'double_dagger': 'double_dagger',
            'per_mille': 'per_mille',
            'per_ten_thousand': 'per_ten_thousand',
        }

        self.file_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
            '.json', '.md', '.txt', '.yml', '.yaml', '.xml', '.sql',
            '.sh', '.bat', '.ps1', '.dockerfile', '.env', '.conf',
            '.ini', '.cfg', '.properties', '.gitignore', '.dockerignore'
        }

        self.results = {
            'files_scanned': 0,
            'files_with_unicode': 0,
            'files_fixed': 0,
            'unicode_issues_found': {},
            'errors': []
        }

    def scan_project(self) -> Dict[str, Any]:
        """Scan the entire project for Unicode issues"""
        print("Scanning wildfire project for Unicode encoding issues...")
        print("=" * 60)

        for file_path in self._get_project_files():
            self.results['files_scanned'] += 1

            try:
                unicode_issues = self._check_file_for_unicode(file_path)
                if unicode_issues:
                    self.results['files_with_unicode'] += 1
                    self.results['unicode_issues_found'][str(file_path)] = unicode_issues
                    print(f"Unicode issues found in: {file_path.relative_to(self.project_root)}")
                    for issue in unicode_issues[:5]:  # Show first 5 issues
                        print(f"  - {issue}")
                    if len(unicode_issues) > 5:
                        print(f"  ... and {len(unicode_issues) - 5} more")

            except Exception as e:
                self.results['errors'].append(f"Error scanning {file_path}: {str(e)}")
                print(f"Error scanning {file_path}: {str(e)}")

        return self.results

    def fix_unicode_issues(self) -> Dict[str, Any]:
        """Fix Unicode issues in all affected files"""
        print(f"\nFixing Unicode issues in {len(self.results['unicode_issues_found'])} files...")
        print("=" * 60)

        for file_path_str, issues in self.results['unicode_issues_found'].items():
            file_path = Path(file_path_str)

            try:
                if self._fix_file_unicode(file_path, issues):
                    self.results['files_fixed'] += 1
                    print(f"Fixed: {file_path.relative_to(self.project_root)}")

            except Exception as e:
                error_msg = f"Error fixing {file_path}: {str(e)}"
                self.results['errors'].append(error_msg)
                print(error_msg)

        return self.results

    def _get_project_files(self) -> List[Path]:
        """Get all relevant project files"""
        files = []

        for root, dirs, filenames in os.walk(self.project_root):
            # Skip common directories that shouldn't be modified
            dirs[:] = [d for d in dirs if not d.startswith('.') and
                      d not in ['__pycache__', 'node_modules', 'build', 'dist', 'venv', 'env']]

            for filename in filenames:
                file_path = Path(root) / filename

                # Check if file should be processed
                if (file_path.suffix.lower() in self.file_extensions or
                    filename in ['Dockerfile', 'Makefile', 'README']):
                    files.append(file_path)

        return files

    def _check_file_for_unicode(self, file_path: Path) -> List[str]:
        """Check a single file for Unicode issues"""
        unicode_issues = []

        try:
            # Try to read with UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for problematic Unicode characters
            for line_num, line in enumerate(content.splitlines(), 1):
                for char in line:
                    if ord(char) > 127:  # Non-ASCII character
                        if char in self.unicode_replacements:
                            unicode_issues.append(f"Line {line_num}: '{char}' -> '{self.unicode_replacements[char]}'")
                        elif ord(char) > 255:  # High Unicode character
                            unicode_issues.append(f"Line {line_num}: Unknown Unicode char '{char}' (U+{ord(char):04X})")

        except UnicodeDecodeError as e:
            unicode_issues.append(f"File encoding error: {str(e)}")
        except Exception as e:
            unicode_issues.append(f"Error reading file: {str(e)}")

        return unicode_issues

    def _fix_file_unicode(self, file_path: Path, issues: List[str]) -> bool:
        """Fix Unicode issues in a single file"""
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply replacements
            original_content = content
            for unicode_char, replacement in self.unicode_replacements.items():
                content = content.replace(unicode_char, replacement)

            # Only write if changes were made
            if content != original_content:
                # Create backup
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                return True

        except Exception as e:
            raise Exception(f"Failed to fix file: {str(e)}")

        return False

    def generate_report(self) -> str:
        """Generate comprehensive fix report"""
        report = []
        report.append("=" * 80)
        report.append("UNICODE ENCODING FIX REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Files Scanned: {self.results['files_scanned']}")
        report.append(f"Files with Unicode Issues: {self.results['files_with_unicode']}")
        report.append(f"Files Successfully Fixed: {self.results['files_fixed']}")
        report.append(f"Errors Encountered: {len(self.results['errors'])}")
        report.append("")

        if self.results['unicode_issues_found']:
            report.append("FILES WITH UNICODE ISSUES:")
            report.append("-" * 40)
            for file_path, issues in self.results['unicode_issues_found'].items():
                relative_path = Path(file_path).relative_to(self.project_root)
                report.append(f"\n{relative_path}:")
                for issue in issues[:3]:  # Show first 3 issues per file
                    report.append(f"  - {issue}")
                if len(issues) > 3:
                    report.append(f"  ... and {len(issues) - 3} more issues")

        if self.results['errors']:
            report.append("\nERRORS ENCOUNTERED:")
            report.append("-" * 40)
            for error in self.results['errors']:
                report.append(f"  - {error}")

        report.append("")
        report.append("UNICODE REPLACEMENTS APPLIED:")
        report.append("-" * 40)
        for unicode_char, replacement in list(self.unicode_replacements.items())[:20]:
            report.append(f"  '{unicode_char}' -> '{replacement}'")
        if len(self.unicode_replacements) > 20:
            report.append(f"  ... and {len(self.unicode_replacements) - 20} more replacements")

        return "\n".join(report)

def main():
    """Main function to run Unicode fixing"""
    project_root = "C:/dev/wildfire"

    if not os.path.exists(project_root):
        print(f"Error: Project directory not found: {project_root}")
        sys.exit(1)

    fixer = UnicodeFixer(project_root)

    # Scan for issues
    print("Step 1: Scanning for Unicode issues...")
    scan_results = fixer.scan_project()

    print(f"\nScan Complete:")
    print(f"  Files scanned: {scan_results['files_scanned']}")
    print(f"  Files with Unicode issues: {scan_results['files_with_unicode']}")

    if scan_results['files_with_unicode'] == 0:
        print("\nNo Unicode issues found! Project is clean.")
        return

    # Fix issues
    print(f"\nStep 2: Fixing Unicode issues...")
    fix_results = fixer.fix_unicode_issues()

    # Generate and save report
    report = fixer.generate_report()
    print(f"\n{report}")

    # Save detailed report
    report_path = os.path.join(project_root, "unicode_fix_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    # Save JSON results
    json_path = os.path.join(project_root, "unicode_fix_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(scan_results, f, indent=2, default=str)

    print(f"\nReports saved:")
    print(f"  Detailed report: {report_path}")
    print(f"  JSON results: {json_path}")

    if fix_results['files_fixed'] > 0:
        print(f"\n[SUCCESS] Fixed Unicode issues in {fix_results['files_fixed']} files!")
        print("Backup files created with .backup extension")
    else:
        print(f"\n[WARNING] No files were fixed. Check error messages above.")

if __name__ == "__main__":
    main()