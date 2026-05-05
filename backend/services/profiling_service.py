import time
import logging
import psutil
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.request_times: Dict[str, List[float]] = defaultdict(list)
        self.db_times: List[float] = []
        self.gemini_times: List[float] = []
        self.start_time = time.time()
        self.process = psutil.Process(os.getpid())
    
    def record_request(self, endpoint: str, duration: float):
        """Record request duration"""
        self.request_times[endpoint].append(duration)
    
    def record_db_operation(self, duration: float):
        """Record database operation duration"""
        self.db_times.append(duration)
    
    def record_gemini_call(self, duration: float):
        """Record Gemini API call duration"""
        self.gemini_times.append(duration)
    
    def get_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_stats(self, data: List[float]) -> Dict:
        """Get statistics for a dataset"""
        if not data:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0
            }
        
        return {
            "count": len(data),
            "min": min(data),
            "max": max(data),
            "avg": sum(data) / len(data),
            "p50": self.get_percentile(data, 50),
            "p95": self.get_percentile(data, 95),
            "p99": self.get_percentile(data, 99)
        }
    
    def get_system_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": self.process.memory_percent(),
                "threads": self.process.num_threads(),
                "uptime_seconds": time.time() - self.start_time
            }
        except Exception as e:
            logger.error(f"[PROFILING] Failed to get system metrics: {e}")
            return {}
    
    def generate_report(self) -> Dict:
        """Generate comprehensive performance report"""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "system": self.get_system_metrics(),
            "endpoints": {},
            "database": self.get_stats(self.db_times),
            "gemini_api": self.get_stats(self.gemini_times),
        }
        
        # Add per-endpoint statistics
        for endpoint, times in self.request_times.items():
            report["endpoints"][endpoint] = self.get_stats(times)
        
        # Identify bottlenecks
        bottlenecks = []
        
        # Check chat endpoint SLA
        if "/api/v1/chat" in self.request_times:
            chat_stats = report["endpoints"]["/api/v1/chat"]
            if chat_stats["p95"] > 15.0:
                bottlenecks.append({
                    "component": "Chat Endpoint",
                    "issue": f"P95 latency ({chat_stats['p95']:.2f}s) exceeds 15s SLA",
                    "severity": "high"
                })
        
        # Check database performance
        if report["database"]["avg"] > 0.1:
            bottlenecks.append({
                "component": "Database",
                "issue": f"Average query time ({report['database']['avg']:.3f}s) is high",
                "severity": "medium"
            })
        
        # Check Gemini API performance
        if report["gemini_api"]["avg"] > 5.0:
            bottlenecks.append({
                "component": "Gemini API",
                "issue": f"Average response time ({report['gemini_api']['avg']:.2f}s) is high",
                "severity": "medium"
            })
        
        # Check memory usage
        if report["system"].get("memory_mb", 0) > 500:
            bottlenecks.append({
                "component": "Memory",
                "issue": f"Memory usage ({report['system']['memory_mb']:.0f}MB) exceeds 500MB target",
                "severity": "low"
            })
        
        report["bottlenecks"] = bottlenecks
        
        # Generate recommendations
        recommendations = []
        
        if bottlenecks:
            for bottleneck in bottlenecks:
                if bottleneck["component"] == "Chat Endpoint":
                    recommendations.append("Consider caching user profiles and conversation history")
                    recommendations.append("Optimize Gemini prompt length")
                elif bottleneck["component"] == "Database":
                    recommendations.append("Add database indexes on frequently queried columns")
                    recommendations.append("Consider connection pooling optimization")
                elif bottleneck["component"] == "Gemini API":
                    recommendations.append("Reduce prompt size by summarizing conversation history")
                    recommendations.append("Consider using a faster Gemini model")
                elif bottleneck["component"] == "Memory":
                    recommendations.append("Implement conversation history cleanup")
                    recommendations.append("Review memory leaks in background tasks")
        
        if not bottlenecks:
            recommendations.append("System is performing within acceptable parameters")
        
        report["recommendations"] = list(set(recommendations))  # Remove duplicates
        
        return report
    
    def print_report(self):
        """Print formatted performance report"""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("PERFORMANCE PROFILING REPORT")
        print("="*80)
        print(f"Generated: {report['generated_at']}")
        print(f"Uptime: {report['uptime_seconds']:.0f} seconds")
        print()
        
        print("SYSTEM METRICS")
        print("-"*80)
        system = report['system']
        print(f"CPU Usage: {system.get('cpu_percent', 0):.1f}%")
        print(f"Memory Usage: {system.get('memory_mb', 0):.0f} MB ({system.get('memory_percent', 0):.1f}%)")
        print(f"Threads: {system.get('threads', 0)}")
        print()
        
        print("ENDPOINT PERFORMANCE")
        print("-"*80)
        for endpoint, stats in report['endpoints'].items():
            print(f"\n{endpoint}")
            print(f"  Requests: {stats['count']}")
            print(f"  Average: {stats['avg']:.3f}s")
            print(f"  P50: {stats['p50']:.3f}s")
            print(f"  P95: {stats['p95']:.3f}s")
            print(f"  P99: {stats['p99']:.3f}s")
            print(f"  Min/Max: {stats['min']:.3f}s / {stats['max']:.3f}s")
        print()
        
        print("DATABASE PERFORMANCE")
        print("-"*80)
        db = report['database']
        print(f"Operations: {db['count']}")
        print(f"Average: {db['avg']:.3f}s")
        print(f"P95: {db['p95']:.3f}s")
        print()
        
        print("GEMINI API PERFORMANCE")
        print("-"*80)
        gemini = report['gemini_api']
        print(f"Calls: {gemini['count']}")
        print(f"Average: {gemini['avg']:.3f}s")
        print(f"P95: {gemini['p95']:.3f}s")
        print()
        
        if report['bottlenecks']:
            print("BOTTLENECKS IDENTIFIED")
            print("-"*80)
            for bottleneck in report['bottlenecks']:
                severity_icon = "🔴" if bottleneck['severity'] == 'high' else "🟡" if bottleneck['severity'] == 'medium' else "🔵"
                print(f"{severity_icon} {bottleneck['component']}: {bottleneck['issue']}")
            print()
        
        print("RECOMMENDATIONS")
        print("-"*80)
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        
        print("\n" + "="*80)


# Global metrics instance
metrics = PerformanceMetrics()
