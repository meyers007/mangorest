"""
MCP (Model Context Protocol) Server for MangoREST.
Automatically exposes @webapi endpoints marked with mcp=True as MCP tools.
This module is only activated when at least one endpoint has mcp=True.
"""
import inspect, json, threading, logging, os
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "MCP Server"
if django_settings:
    MCP_SERVER_NAME = getattr(django_settings, "MCP_SERVER_NAME", "MCP Server")

# Registry of MCP-enabled tools
_MCP_TOOLS = {}
_mcp_server_started = False

try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.debug("MCP package not installed. Install with: pip install mcp[cli]")


def register_tool(url, func, argspec, auth, opts):
    """Register a webapi endpoint as an MCP tool.
    Called from mango.py when @webapi(..., mcp=True) is used.
    """
    tool_name = url.strip("/").replace("/", "_").replace(".", "_")
    docstring = inspect.getdoc(func) or opts.get("doc", f"API endpoint: {url}")

    # Extract parameter info (excluding 'request' and 'self')
    args = list(argspec.args or [])
    defaults = list(argspec.defaults or [])
    args = [a for a in args if a not in ("request", "self")]
    pad = len(args) - len(defaults)

    params = []
    for i, arg in enumerate(args):
        default = defaults[i - pad] if i >= pad else None
        params.append({
            "name": arg,
            "default": default,
            "required": i < pad,
        })

    has_kwargs = argspec.varkw is not None

    _MCP_TOOLS[url] = {
        "name": tool_name,
        "func": func,
        "argspec": argspec,
        "auth": auth,
        "opts": opts,
        "params": params,
        "has_kwargs": has_kwargs,
        "docstring": docstring,
        "url": url,
    }
    logger.info(f"MCP tool registered: {tool_name} -> {url}")
    __NAME__    = "Sada MCP Server"

    if  get_mcp_count() > 0 and not get_server_status()["started"]:
        start_server(name=MCP_SERVER_NAME)


def get_mcp_tools():
    """Return the registry of MCP tools."""
    return _MCP_TOOLS


def get_mcp_count():
    """Return the number of registered MCP tools."""
    return len(_MCP_TOOLS)


def is_mcp_endpoint(url):
    """Check if a URL is registered as an MCP tool."""
    return url in _MCP_TOOLS


def _create_mcp_server(name="MangoREST MCP Server"):
    """Create and configure an MCP server with all registered tools."""
    if not MCP_AVAILABLE:
        logger.warning("Cannot create MCP server: mcp package not installed.")
        return None

    mcp = FastMCP(name)

    for url, tool_info in _MCP_TOOLS.items():
        func = tool_info["func"]
        tool_name = tool_info["name"]
        docstring = tool_info["docstring"]
        params = tool_info["params"]
        has_kwargs = tool_info["has_kwargs"]

        # Create a wrapper that calls the original function
        # MCP tools receive params as kwargs, we simulate a request-like object
        def _make_tool_handler(f, param_list, accepts_kwargs):
            def tool_handler(**kwargs):
                """Execute the API endpoint."""
                try:
                    # Create a minimal request-like object
                    req = _MinimalRequest(kwargs)
                    result = f(req, **kwargs)
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, indent=2, default=str)
                    return str(result)
                except Exception as e:
                    return f"Error: {str(e)}"

            # Set proper metadata
            tool_handler.__name__ = f.__name__
            tool_handler.__doc__ = f.__doc__
            return tool_handler

        handler = _make_tool_handler(func, params, has_kwargs)
        mcp.tool(name=tool_name, description=docstring)(handler)

    return mcp


class _MinimalRequest:
    """Minimal request-like object for MCP tool calls."""

    def __init__(self, params=None):
        self._params = params or {}
        self.method = "MCP"
        self.GET = self._params
        self.POST = self._params
        self.META = {}
        self.COOKIES = {}

    def __repr__(self):
        return f"<MCPRequest params={self._params}>"


def start_server(name="MangoREST MCP Server", transport="stdio"):
    """Start the MCP server if there are registered tools.
    
    Args:
        name: Name of the MCP server
        transport: Transport method - 'stdio' or 'sse'
    
    Returns:
        True if server started, False otherwise
    """
    global _mcp_server_started

    if _mcp_server_started:
        logger.info("MCP server already started.")
        return True

    if not _MCP_TOOLS:
        logger.debug("No MCP tools registered, skipping server start.")
        return False

    if not MCP_AVAILABLE:
        logger.warning(
            f"MCP package not installed but {len(_MCP_TOOLS)} tools registered. "
            "Install with: pip install mcp[cli]"
        )
        return False

    mcp = _create_mcp_server(name)
    if not mcp:
        return False

    def _run_server():
        try:
            logger.info(
                f"Starting MCP server '{name}' with {len(_MCP_TOOLS)} tools "
                f"via {transport} transport"
            )
            mcp.run(transport=transport)
        except Exception as e:
            logger.error(f"MCP server error: {e}")

    # Run MCP server in a background thread so it doesn't block Django
    thread = threading.Thread(target=_run_server, daemon=True, name="mcp-server")
    thread.start()
    _mcp_server_started = True
    logger.info(f"MCP server thread started with {len(_MCP_TOOLS)} tools")
    return True


def get_server_status():
    """Return a dict with MCP server status info."""
    return {
        "available": MCP_AVAILABLE,
        "started": _mcp_server_started,
        "tool_count": len(_MCP_TOOLS),
        "tools": list(_MCP_TOOLS.keys()),
    }
