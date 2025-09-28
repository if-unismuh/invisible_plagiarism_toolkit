# performance_monitor.py
"""
Performance monitoring and metrics collection
Real-time performance tracking and optimization suggestions
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: str
    processing_time: float
    memory_usage_mb: float
    cpu_percent: float
    file_size_mb: float
    chars_processed: int
    substitutions_made: int
    processing_rate: float  # chars per second
    memory_efficiency: float  # chars per MB
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class SystemResources:
    """System resource information"""
    total_memory_gb: float
    available_memory_gb: float
    cpu_count: int
    cpu_freq_mhz: float
    
    def to_dict(self) -> Dict:
        return asdict(self)

class PerformanceMonitor:
    """Real-time performance monitoring and optimization"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.metrics_history: List[PerformanceMetrics] = []
        self.system_info = self._get_system_info()
        self.monitoring_active = False
        self._monitor_thread = None
        
    def _get_system_info(self) -> SystemResources:
        """Get system resource information"""
        memory = psutil.virtual_memory()
        cpu_freq = psutil.cpu_freq()
        
        return SystemResources(
            total_memory_gb=memory.total / (1024**3),
            available_memory_gb=memory.available / (1024**3),
            cpu_count=psutil.cpu_count(),
            cpu_freq_mhz=cpu_freq.current if cpu_freq else 0
        )
    
    def start_monitoring(self, interval: float = 1.0):
        """Start background performance monitoring"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self, interval: float):
        """Background monitoring loop"""
        while self.monitoring_active:
            # Record current system state
            current_memory = psutil.virtual_memory().used / (1024**2)  # MB
            current_cpu = psutil.cpu_percent(interval=0.1)
            
            # Store for analysis
            self._last_memory = current_memory
            self._last_cpu = current_cpu
            
            time.sleep(interval)
    
    def measure_operation(self, operation: Callable, *args, **kwargs) -> tuple:
        """Measure performance of an operation"""
        # Get initial state
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024**2)  # MB
        start_time = time.perf_counter()
        
        # Execute operation
        result = operation(*args, **kwargs)
        
        # Calculate metrics
        end_time = time.perf_counter()
        final_memory = process.memory_info().rss / (1024**2)  # MB
        processing_time = end_time - start_time
        
        return result, processing_time, final_memory - initial_memory
    
    def record_processing_metrics(
        self,
        processing_time: float,
        file_size_bytes: int,
        chars_processed: int,
        substitutions_made: int
    ) -> PerformanceMetrics:
        """Record metrics from document processing"""
        
        # Get current system state
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
        
        # Calculate derived metrics
        file_size_mb = file_size_bytes / (1024**2)
        processing_rate = chars_processed / processing_time if processing_time > 0 else 0
        memory_efficiency = chars_processed / memory_info.used * (1024**2) if memory_info.used > 0 else 0
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time,
            memory_usage_mb=memory_info.used / (1024**2),
            cpu_percent=cpu_percent,
            file_size_mb=file_size_mb,
            chars_processed=chars_processed,
            substitutions_made=substitutions_made,
            processing_rate=processing_rate,
            memory_efficiency=memory_efficiency
        )
        
        self.metrics_history.append(metrics)
        
        # Save to log file if specified
        if self.log_file:
            self._save_metrics(metrics)
        
        return metrics
    
    def _save_metrics(self, metrics: PerformanceMetrics):
        """Save metrics to log file"""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'a', encoding='utf-8') as f:
            json.dump(metrics.to_dict(), f)
            f.write('\n')
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary statistics"""
        if not self.metrics_history:
            return {"message": "No metrics recorded yet"}
        
        # Calculate statistics
        processing_times = [m.processing_time for m in self.metrics_history]
        processing_rates = [m.processing_rate for m in self.metrics_history]
        memory_usage = [m.memory_usage_mb for m in self.metrics_history]
        
        return {
            "total_operations": len(self.metrics_history),
            "avg_processing_time": sum(processing_times) / len(processing_times),
            "max_processing_time": max(processing_times),
            "min_processing_time": min(processing_times),
            "avg_processing_rate": sum(processing_rates) / len(processing_rates),
            "avg_memory_usage_mb": sum(memory_usage) / len(memory_usage),
            "max_memory_usage_mb": max(memory_usage),
            "system_info": self.system_info.to_dict()
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """Generate optimization suggestions based on metrics"""
        suggestions = []
        
        if not self.metrics_history:
            return ["Process some documents first to get optimization suggestions"]
        
        summary = self.get_performance_summary()
        
        # Processing time suggestions
        if summary["avg_processing_time"] > 30:
            suggestions.append("Consider reducing substitution rates for faster processing")
        
        if summary["max_processing_time"] > 60:
            suggestions.append("Large files detected - consider batch processing")
        
        # Memory usage suggestions
        if summary["max_memory_usage_mb"] > self.system_info.available_memory_gb * 1024 * 0.8:
            suggestions.append("High memory usage detected - process smaller batches")
        
        # Processing rate suggestions
        if summary["avg_processing_rate"] < 500:
            suggestions.append("Low processing rate - disable unused techniques")
        
        # System-specific suggestions
        if self.system_info.cpu_count < 4:
            suggestions.append("Limited CPU cores - avoid concurrent processing")
        
        if self.system_info.total_memory_gb < 8:
            suggestions.append("Limited RAM - process files individually")
        
        if not suggestions:
            suggestions.append("Performance appears optimal for current system")
        
        return suggestions
    
    def benchmark_system(self) -> Dict:
        """Run system benchmark for performance baseline"""
        print("Running system benchmark...")
        
        # Test data
        test_sizes = [1000, 10000, 100000]  # Character counts
        benchmark_results = {}
        
        from unicode_steganography import UnicodeSteg
        steg = UnicodeSteg()
        
        for size in test_sizes:
            # Create test text
            test_text = "a" * size
            
            # Measure Unicode substitution
            start_time = time.perf_counter()
            result = steg.apply_substitution(test_text, rate=0.05)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            rate = size / processing_time if processing_time > 0 else 0
            
            benchmark_results[f"{size}_chars"] = {
                "processing_time": processing_time,
                "processing_rate": rate,
                "rate_category": self._categorize_rate(rate)
            }
        
        return {
            "system_info": self.system_info.to_dict(),
            "benchmark_results": benchmark_results,
            "recommendations": self._get_benchmark_recommendations(benchmark_results)
        }
    
    def _categorize_rate(self, rate: float) -> str:
        """Categorize processing rate"""
        if rate > 10000:
            return "excellent"
        elif rate > 5000:
            return "good"
        elif rate > 1000:
            return "average"
        else:
            return "slow"
    
    def _get_benchmark_recommendations(self, results: Dict) -> List[str]:
        """Get recommendations based on benchmark results"""
        recommendations = []
        
        # Check largest test performance
        large_test = results.get("100000_chars", {})
        if large_test.get("rate_category") == "slow":
            recommendations.append("System may struggle with large documents - use smaller files")
        
        # Check if performance degrades with size
        small_rate = results.get("1000_chars", {}).get("processing_rate", 0)
        large_rate = results.get("100000_chars", {}).get("processing_rate", 0)
        
        if large_rate < small_rate * 0.5:
            recommendations.append("Performance degrades with file size - consider chunked processing")
        
        return recommendations
    
    def export_metrics(self, output_file: str):
        """Export all metrics to JSON file"""
        export_data = {
            "system_info": self.system_info.to_dict(),
            "summary": self.get_performance_summary(),
            "metrics_history": [m.to_dict() for m in self.metrics_history],
            "optimization_suggestions": self.get_optimization_suggestions(),
            "export_timestamp": datetime.now().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Metrics exported to: {output_file}")

# Context manager for automatic performance monitoring
class PerformanceContext:
    """Context manager for automatic performance measurement"""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        processing_time = self.end_time - self.start_time
        
        print(f"{self.operation_name} completed in {processing_time:.2f}s")
        
        # Record basic timing
        self.monitor.metrics_history.append(
            PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                processing_time=processing_time,
                memory_usage_mb=psutil.virtual_memory().used / (1024**2),
                cpu_percent=psutil.cpu_percent(),
                file_size_mb=0,  # Not available in this context
                chars_processed=0,  # Not available in this context
                substitutions_made=0,  # Not available in this context
                processing_rate=0,
                memory_efficiency=0
            )
        )

# Decorator for automatic performance measurement
def monitor_performance(monitor: PerformanceMonitor):
    """Decorator to automatically monitor function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceContext(monitor, func.__name__):
                return func(*args, **kwargs)
        return wrapper
    return decorator
