import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat() + "Z",
            "metadata": self.metadata,
        }


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "0.1.0"
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "checks": [c.to_dict() for c in self.checks],
        }


HealthCheckFunc = Callable[[], Coroutine[Any, Any, HealthCheckResult]]


class HealthCheckManager:
    """
    Health check management system.
    
    Runs periodic health checks for:
    - Database connectivity
    - API response times
    - External dependencies
    - Memory/CPU usage
    - Disk space
    
    Provides:
    - /v1/health endpoint (liveness)
    - /v1/health/ready endpoint (readiness)
    - /v1/health/detailed endpoint (full diagnostics)
    """
    
    def __init__(
        self,
        check_interval_seconds: int = 30,
        timeout_seconds: float = 5.0,
    ):
        self.check_interval = check_interval_seconds
        self.timeout = timeout_seconds
        self._checks: Dict[str, HealthCheckFunc] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._start_time = time.time()
        self.logger = logging.getLogger("citadel.health")
    
    def register(self, name: str, check_func: HealthCheckFunc) -> None:
        """Register a health check."""
        self._checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a single health check."""
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not registered",
                response_time_ms=0.0,
            )
        
        start = time.time()
        try:
            result = await asyncio.wait_for(
                self._checks[name](),
                timeout=self.timeout,
            )
            result.response_time_ms = (time.time() - start) * 1000
            self._last_results[name] = result
            return result
        except asyncio.TimeoutError:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {self.timeout}s",
                response_time_ms=self.timeout * 1000,
            )
            self._last_results[name] = result
            return result
        except (OSError, ValueError, TypeError, RuntimeError, ConnectionError, TimeoutError) as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed ({type(e).__name__}): {str(e)}",
                response_time_ms=(time.time() - start) * 1000,
            )
            self._last_results[name] = result
            return result
    
    async def run_all_checks(self) -> SystemHealth:
        """Run all registered health checks."""
        results = await asyncio.gather(
            *[self.run_check(name) for name in self._checks.keys()],
            return_exceptions=True,
        )
        
        checks = []
        overall_status = HealthStatus.HEALTHY
        
        for result in results:
            if isinstance(result, Exception):
                checks.append(HealthCheckResult(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check crashed: {str(result)}",
                    response_time_ms=0.0,
                ))
                overall_status = HealthStatus.UNHEALTHY
            else:
                checks.append(result)
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        return SystemHealth(
            status=overall_status,
            checks=checks,
            uptime_seconds=time.time() - self._start_time,
        )
    
    def get_last_result(self, name: str) -> Optional[HealthCheckResult]:
        """Get the last result for a specific check."""
        return self._last_results.get(name)
    
    # Built-in health checks
    
    @staticmethod
    def create_db_check(db_pool) -> HealthCheckFunc:
        """Create a database health check."""
        async def check() -> HealthCheckResult:
            start = time.time()
            try:
                async with db_pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    if result == 1:
                        return HealthCheckResult(
                            name="database",
                            status=HealthStatus.HEALTHY,
                            message="Database connection OK",
                            response_time_ms=(time.time() - start) * 1000,
                            metadata={"pool_size": db_pool.get_size()},
                        )
                    else:
                        return HealthCheckResult(
                            name="database",
                            status=HealthStatus.UNHEALTHY,
                            message="Database returned unexpected result",
                            response_time_ms=(time.time() - start) * 1000,
                        )
            except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Database connection failed ({type(e).__name__}): {str(e)}",
                    response_time_ms=(time.time() - start) * 1000,
                )
        return check
    
    @staticmethod
    def create_memory_check(threshold_mb: int = 500) -> HealthCheckFunc:
        """Create a memory usage health check."""
        async def check() -> HealthCheckResult:
            import psutil
            try:
                process = psutil.Process()
                mem_mb = process.memory_info().rss / (1024 * 1024)
                status = HealthStatus.HEALTHY if mem_mb < threshold_mb else HealthStatus.DEGRADED
                return HealthCheckResult(
                    name="memory",
                    status=status,
                    message=f"Memory usage: {mem_mb:.1f}MB",
                    response_time_ms=0.0,
                    metadata={"memory_mb": mem_mb, "threshold_mb": threshold_mb},
                )
            except (OSError, ValueError, TypeError, RuntimeError) as e:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.UNKNOWN,
                    message=f"Could not check memory ({type(e).__name__}): {str(e)}",
                    response_time_ms=0.0,
                )
        return check
    
    @staticmethod
    def create_disk_check(threshold_percent: float = 90.0) -> HealthCheckFunc:
        """Create a disk space health check."""
        async def check() -> HealthCheckResult:
            import shutil
            try:
                usage = shutil.disk_usage("/")
                used_percent = (usage.used / usage.total) * 100
                status = HealthStatus.HEALTHY if used_percent < threshold_percent else HealthStatus.DEGRADED
                return HealthCheckResult(
                    name="disk",
                    status=status,
                    message=f"Disk usage: {used_percent:.1f}%",
                    response_time_ms=0.0,
                    metadata={
                        "used_percent": used_percent,
                        "threshold_percent": threshold_percent,
                        "total_gb": usage.total / (1024**3),
                        "free_gb": usage.free / (1024**3),
                    },
                )
            except (OSError, ValueError, TypeError, RuntimeError) as e:
                return HealthCheckResult(
                    name="disk",
                    status=HealthStatus.UNKNOWN,
                    message=f"Could not check disk ({type(e).__name__}): {str(e)}",
                    response_time_ms=0.0,
                )
        return check
    
    @staticmethod
    def create_api_check(base_url: str, endpoint: str = "/v1/health/live") -> HealthCheckFunc:
        """Create an API self-check."""
        async def check() -> HealthCheckResult:
            import aiohttp
            start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{base_url}{endpoint}",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            return HealthCheckResult(
                                name="api_self_check",
                                status=HealthStatus.HEALTHY,
                                message=f"API responds with {response.status}",
                                response_time_ms=(time.time() - start) * 1000,
                            )
                        else:
                            return HealthCheckResult(
                                name="api_self_check",
                                status=HealthStatus.DEGRADED,
                                message=f"API returned {response.status}",
                                response_time_ms=(time.time() - start) * 1000,
                            )
            except (aiohttp.ClientError, ConnectionError, TimeoutError, OSError, ValueError, TypeError) as e:
                return HealthCheckResult(
                    name="api_self_check",
                    status=HealthStatus.UNHEALTHY,
                    message=f"API self-check failed ({type(e).__name__}): {str(e)}",
                    response_time_ms=(time.time() - start) * 1000,
                )
        return check


# Global instance
_health_manager: Optional[HealthCheckManager] = None


def get_health_manager() -> HealthCheckManager:
    """Get or create the global health check manager."""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager