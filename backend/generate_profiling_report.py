#!/usr/bin/env python3
"""
Generate a comprehensive profiling report for the Gemini Chatbot API.
Run this script after the server has been running for a while to collect metrics.
"""

import requests
import json
import sys
from datetime import datetime

def generate_report(api_url: str = "http://localhost:8000"):
    """Generate and save profiling report"""
    
    print("="*80)
    print("GEMINI CHATBOT - PROFILING REPORT GENERATOR")
    print("="*80)
    print(f"API URL: {api_url}")
    print(f"Generated: {datetime.now().isoformat()}")
    print()
    
    try:
        # Fetch metrics from API
        print("Fetching metrics from /metrics endpoint...")
        response = requests.get(f"{api_url}/metrics", timeout=10)
        response.raise_for_status()
        metrics = response.json()
        
        # Generate markdown report
        report = generate_markdown_report(metrics, api_url)
        
        # Save to file
        filename = f"PROFILING_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n✅ Report saved to: {filename}")
        print("\nSummary:")
        print(f"  - Total Endpoints: {len(metrics.get('endpoints', {}))}")
        print(f"  - Total Requests: {sum(e['count'] for e in metrics.get('endpoints', {}).values())}")
        print(f"  - Bottlenecks Found: {len(metrics.get('bottlenecks', []))}")
        print(f"  - Uptime: {metrics.get('uptime_seconds', 0):.0f} seconds")
        
        # Print bottlenecks if any
        if metrics.get('bottlenecks'):
            print("\n⚠️  Bottlenecks Identified:")
            for b in metrics['bottlenecks']:
                print(f"  - {b['component']}: {b['issue']}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: Could not connect to API at {api_url}")
        print("   Make sure the server is running.")
        return False
    except requests.exceptions.Timeout:
        print(f"\n❌ Error: Request timed out")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def generate_markdown_report(metrics: dict, api_url: str) -> str:
    """Generate markdown formatted report"""
    
    report = f"""# Performance Profiling Report

**Generated:** {metrics.get('generated_at', 'N/A')}  
**API URL:** {api_url}  
**Uptime:** {metrics.get('uptime_seconds', 0):.0f} seconds ({metrics.get('uptime_seconds', 0)/3600:.1f} hours)

---

## Executive Summary

"""
    
    # Calculate totals
    total_requests = sum(e['count'] for e in metrics.get('endpoints', {}).values())
    total_db_ops = metrics.get('database', {}).get('count', 0)
    total_gemini_calls = metrics.get('gemini_api', {}).get('count', 0)
    
    report += f"""
- **Total API Requests:** {total_requests}
- **Total Database Operations:** {total_db_ops}
- **Total Gemini API Calls:** {total_gemini_calls}
- **Bottlenecks Identified:** {len(metrics.get('bottlenecks', []))}

"""
    
    # System Metrics
    system = metrics.get('system', {})
    report += f"""
---

## System Metrics

| Metric | Value |
|--------|-------|
| CPU Usage | {system.get('cpu_percent', 0):.1f}% |
| Memory Usage | {system.get('memory_mb', 0):.0f} MB ({system.get('memory_percent', 0):.1f}%) |
| Threads | {system.get('threads', 0)} |
| Uptime | {system.get('uptime_seconds', 0):.0f} seconds |

"""
    
    # Endpoint Performance
    report += """
---

## Endpoint Performance

### Response Time Statistics

| Endpoint | Requests | Avg (s) | P50 (s) | P95 (s) | P99 (s) | Min (s) | Max (s) |
|----------|----------|---------|---------|---------|---------|---------|---------|
"""
    
    for endpoint, stats in metrics.get('endpoints', {}).items():
        report += f"| `{endpoint}` | {stats['count']} | {stats['avg']:.3f} | {stats['p50']:.3f} | {stats['p95']:.3f} | {stats['p99']:.3f} | {stats['min']:.3f} | {stats['max']:.3f} |\n"
    
    # SLA Compliance
    report += """
---

## SLA Compliance

**Target:** Chat endpoint P95 latency < 15 seconds

"""
    
    chat_endpoint = None
    for endpoint in metrics.get('endpoints', {}).keys():
        if 'chat' in endpoint.lower():
            chat_endpoint = endpoint
            break
    
    if chat_endpoint:
        chat_stats = metrics['endpoints'][chat_endpoint]
        p95 = chat_stats['p95']
        status = "✅ PASS" if p95 < 15 else "❌ FAIL"
        report += f"**Status:** {status}  \n"
        report += f"**Actual P95:** {p95:.3f} seconds  \n"
        if p95 >= 15:
            report += f"**Deviation:** +{p95 - 15:.3f} seconds over target  \n"
    else:
        report += "**Status:** ⚠️ No chat endpoint data available\n"
    
    # Database Performance
    db = metrics.get('database', {})
    report += f"""
---

## Database Performance

| Metric | Value |
|--------|-------|
| Total Operations | {db.get('count', 0)} |
| Average Time | {db.get('avg', 0):.3f}s |
| P50 | {db.get('p50', 0):.3f}s |
| P95 | {db.get('p95', 0):.3f}s |
| P99 | {db.get('p99', 0):.3f}s |
| Min/Max | {db.get('min', 0):.3f}s / {db.get('max', 0):.3f}s |

"""
    
    # Gemini API Performance
    gemini = metrics.get('gemini_api', {})
    report += f"""
---

## Gemini API Performance

| Metric | Value |
|--------|-------|
| Total Calls | {gemini.get('count', 0)} |
| Average Time | {gemini.get('avg', 0):.3f}s |
| P50 | {gemini.get('p50', 0):.3f}s |
| P95 | {gemini.get('p95', 0):.3f}s |
| P99 | {gemini.get('p99', 0):.3f}s |
| Min/Max | {gemini.get('min', 0):.3f}s / {gemini.get('max', 0):.3f}s |

"""
    
    # Bottlenecks
    bottlenecks = metrics.get('bottlenecks', [])
    if bottlenecks:
        report += """
---

## Bottlenecks Identified

"""
        for b in bottlenecks:
            severity_icon = "🔴" if b['severity'] == 'high' else "🟡" if b['severity'] == 'medium' else "🔵"
            report += f"### {severity_icon} {b['component']}\n\n"
            report += f"**Issue:** {b['issue']}  \n"
            report += f"**Severity:** {b['severity'].upper()}  \n\n"
    else:
        report += """
---

## Bottlenecks Identified

✅ No significant bottlenecks detected. System is performing within acceptable parameters.

"""
    
    # Recommendations
    recommendations = metrics.get('recommendations', [])
    report += """
---

## Recommendations

"""
    
    for i, rec in enumerate(recommendations, 1):
        report += f"{i}. {rec}\n"
    
    # Conclusion
    report += """
---

## Conclusion

"""
    
    if not bottlenecks:
        report += "The system is performing well with no critical issues identified. Continue monitoring for any changes in traffic patterns.\n"
    elif any(b['severity'] == 'high' for b in bottlenecks):
        report += "⚠️ **Action Required:** High-severity bottlenecks detected. Immediate optimization recommended.\n"
    else:
        report += "The system is functional but has some areas for optimization. Review recommendations above.\n"
    
    report += f"""
---

**Report Generated:** {datetime.now().isoformat()}  
**Tool Version:** 1.0  
**Next Review:** Recommended after implementing optimizations
"""
    
    return report


if __name__ == "__main__":
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = generate_report(api_url)
    sys.exit(0 if success else 1)
