#!/usr/bin/env python3
"""Quick demo of the accessibility auditor system"""

import sys
sys.path.insert(0, '.')

from src.pipeline import run_audit_pipeline
from src.pdf_reporter import generate_pdf_report
import time

print('[STARTING] Running Accessibility Auditor Pipeline...\n')
start = time.time()

try:
    report, pipeline = run_audit_pipeline(
        city_name='Demo City',
        stops_source='data/demo_stops.csv',
        grievances_source='data/demo_grievances.csv'
    )
    elapsed = time.time() - start
    
    print('\n[SUCCESS] AUDIT COMPLETE\n')
    print(f'[TIME] Execution Time: {elapsed:.2f}s')
    print(f'[STOPS] Stops Audited: {report.total_stops_audited}')
    print(f'[GRIEVANCES] Grievances Analyzed: {report.total_grievances_analyzed}')
    print(f'[COVERAGE] Network Coverage: {report.coverage_percent:.1f}%')
    print(f'[SCORE] Average Gap Score: {report.avg_gap_score:.1f}/100')
    
    print(f'\n[PRIORITY] Priority Breakdown:')
    print(f'   CRITICAL: {report.stops_by_priority.get("CRITICAL", 0)}')
    print(f'   HIGH: {report.stops_by_priority.get("HIGH", 0)}')
    print(f'   MEDIUM: {report.stops_by_priority.get("MEDIUM", 0)}')
    print(f'   LOW: {report.stops_by_priority.get("LOW", 0)}')
    
    print(f'\n[THEMES] Top Grievance Themes:')
    for theme in report.grievance_themes[:5]:
        print(f'   * {theme.theme}: {theme.count} complaints')
    
    print(f'\n[TOP-STOPS] Top 5 Priority Stops:')
    for i, stop in enumerate(report.top_priority_stops[:5], 1):
        print(f'   {i}. {stop.stop_name} (Gap: {stop.gap_score:.1f}/100, Priority: {stop.priority_level})')
    
    # Generate PDF report
    print('\n[PDF] Generating PDF Report...')
    pdf_bytes = generate_pdf_report(report)
    with open('Demo_City_Accessibility_Report.pdf', 'wb') as f:
        f.write(pdf_bytes)
    print(f'[SAVED] PDF: Demo_City_Accessibility_Report.pdf ({len(pdf_bytes)/1024:.1f} KB)')
    
    print('\n' + '='*60)
    print('[COMPLETE] System is fully functional and ready to use!')
    print('='*60)
    
except Exception as e:
    print(f'\n[ERROR] Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
