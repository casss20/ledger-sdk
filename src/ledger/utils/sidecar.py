"""
Sidecar Pattern — Ledger SDK

Like Weft's "Infrastructure as nodes, sidecars as the bridge":
- Infrastructure nodes provision real resources
- Consumer nodes talk through sidecars via HTTP
- Sidecar is the only thing with real connections
- Security boundary, language freedom, isolation
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

# Optional aiohttp import
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    aiohttp = None
    HAS_AIOHTTP = False
    logger.warning("[Sidecar] aiohttp not installed. Sidecar features disabled. Install with: pip install ledger-sdk[sidecar]")


class SidecarError(Exception):
    """Error communicating with sidecar."""
    pass


class SidecarTimeoutError(SidecarError):
    """Sidecar did not respond in time."""
    pass


@runtime_checkable
class Sidecar(Protocol):
    """
    Protocol for sidecar implementations.
    Like Weft's sidecar interface.
    """
    
    async def action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action on the sidecar."""
        ...
    
    async def health(self) -> bool:
        """Check if sidecar is healthy."""
        ...
    
    async def outputs(self) -> Dict[str, Any]:
        """Get runtime outputs (connection info, etc)."""
        ...


class SidecarClient:
    """
    HTTP client for sidecar communication.
    Like Weft's InfraClient.
    """
    
    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        retries: int = 3
    ):
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp not installed. Install with: pip install ledger-sdk[sidecar]")
        self.endpoint = endpoint.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self._session: Optional[Any] = None
    
    async def _get_session(self) -> Any:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session
    
    async def action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /action to the sidecar.
        Like Weft's sidecar action endpoint.
        """
        session = await self._get_session()
        url = f"{self.endpoint}/action"
        
        for attempt in range(self.retries):
            try:
                async with session.post(
                    url,
                    json={"action": action, "payload": payload}
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.debug(f"[SidecarClient] Action {action} succeeded")
                        return result
                    else:
                        text = await resp.text()
                        raise SidecarError(f"Sidecar returned {resp.status}: {text}")
                        
            except aiohttp.ClientError as e:
                if attempt < self.retries - 1:
                    logger.warning(f"[SidecarClient] Attempt {attempt + 1} failed: {e}")
                    continue
                raise SidecarError(f"Failed to contact sidecar after {self.retries} attempts: {e}")
        
        raise SidecarError("All retries exhausted")
    
    async def health(self) -> bool:
        """GET /health to check liveness."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.endpoint}/health",
                timeout=aiohttp.ClientTimeout(total=5.0)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"[SidecarClient] Health check failed: {e}")
            return False
    
    async def outputs(self) -> Dict[str, Any]:
        """GET /outputs for runtime values."""
        session = await self._get_session()
        async with session.get(f"{self.endpoint}/outputs") as resp:
            if resp.status == 200:
                return await resp.json()
            raise SidecarError(f"Failed to get outputs: {resp.status}")
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


class PostgresSidecar:
    """
    Sidecar for PostgreSQL operations.
    Core never talks to Postgres directly.
    """
    
    def __init__(self, endpoint: str):
        self.client = SidecarClient(endpoint)
        self._connection_info: Optional[Dict] = None
    
    async def initialize(self):
        """Get connection info from sidecar."""
        self._connection_info = await self.client.outputs()
        logger.info(f"[PostgresSidecar] Connected to {self._connection_info.get('host')}")
    
    async def query(self, sql: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a query through the sidecar."""
        return await self.client.action("query", {
            "sql": sql,
            "params": params or {}
        })
    
    async def execute(self, sql: str) -> Dict[str, Any]:
        """Execute a statement (INSERT, UPDATE, DELETE)."""
        return await self.client.action("execute", {"sql": sql})
    
    async def health(self) -> bool:
        return await self.client.health()
    
    async def close(self):
        await self.client.close()


class RedisSidecar:
    """Sidecar for Redis operations."""
    
    def __init__(self, endpoint: str):
        self.client = SidecarClient(endpoint)
    
    async def get(self, key: str) -> Optional[str]:
        result = await self.client.action("get", {"key": key})
        return result.get("value")
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        result = await self.client.action("set", {
            "key": key,
            "value": value,
            "ttl": ttl
        })
        return result.get("success", False)
    
    async def delete(self, key: str) -> bool:
        result = await self.client.action("delete", {"key": key})
        return result.get("success", False)


class WhatsAppSidecar:
    """Sidecar for WhatsApp messaging."""
    
    def __init__(self, endpoint: str):
        self.client = SidecarClient(endpoint)
    
    async def send_message(self, to: str, body: str) -> Dict[str, Any]:
        return await self.client.action("send_message", {
            "to": to,
            "body": body
        })
    
    async def send_template(self, to: str, template_name: str, params: Dict) -> Dict[str, Any]:
        return await self.client.action("send_template", {
            "to": to,
            "template": template_name,
            "params": params
        })


class SidecarRegistry:
    """
    Registry for managing sidecars.
    Like Weft's infrastructure node registry.
    """
    
    def __init__(self):
        self._sidecars: Dict[str, Sidecar] = {}
        self._endpoints: Dict[str, str] = {}
    
    def register(self, name: str, sidecar: Sidecar, endpoint: str):
        """Register a sidecar."""
        self._sidecars[name] = sidecar
        self._endpoints[name] = endpoint
        logger.info(f"[SidecarRegistry] Registered {name} at {endpoint}")
    
    def get(self, name: str) -> Optional[Sidecar]:
        """Get a registered sidecar."""
        return self._sidecars.get(name)
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all registered sidecars."""
        results = {}
        for name, sidecar in self._sidecars.items():
            try:
                results[name] = await sidecar.health()
            except Exception as e:
                logger.error(f"[SidecarRegistry] Health check failed for {name}: {e}")
                results[name] = False
        return results
    
    async def close_all(self):
        """Close all sidecar connections."""
        for name, sidecar in self._sidecars.items():
            try:
                if hasattr(sidecar, 'close'):
                    await sidecar.close()
            except Exception as e:
                logger.error(f"[SidecarRegistry] Failed to close {name}: {e}")


# Singleton
_registry_instance: Optional[SidecarRegistry] = None


def get_sidecar_registry() -> SidecarRegistry:
    """Get or create the global sidecar registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SidecarRegistry()
    return _registry_instance


# Convenience aliases
register_sidecar = lambda name, sc, ep: get_sidecar_registry().register(name, sc, ep)
get_sidecar = lambda name: get_sidecar_registry().get(name)

__all__ = [
    'Sidecar',
    'SidecarClient',
    'SidecarError',
    'SidecarTimeoutError',
    'PostgresSidecar',
    'RedisSidecar',
    'WhatsAppSidecar',
    'SidecarRegistry',
    'get_sidecar_registry',
    'register_sidecar',
    'get_sidecar',
]
