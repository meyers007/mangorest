"""
Swagger-like API Documentation Generator for MangoREST.
Generates a cached, interactive HTML page from registered routes.
"""
import json
import hashlib
import inspect

_cache = {"html": None, "hash": None}


def _get_routes_hash(routes):
    """Hash the current routes to detect changes."""
    keys = sorted(routes.keys())
    return hashlib.md5(json.dumps(keys).encode()).hexdigest()


def _get_param_info(argspec):
    """Extract parameter details from function argspec."""
    params = []
    args = list(argspec.args or [])
    defaults = list(argspec.defaults or [])

    # Remove 'request' and 'self' from args
    args = [a for a in args if a not in ("request", "self")]

    # Align defaults with args (defaults are right-aligned)
    pad = len(args) - len(defaults)
    for i, arg in enumerate(args):
        default = defaults[i - pad] if i >= pad else None
        param_type = "string"
        if default is not None:
            if isinstance(default, int):
                param_type = "integer"
            elif isinstance(default, float):
                param_type = "number"
            elif isinstance(default, bool):
                param_type = "boolean"
        params.append({
            "name": arg,
            "type": param_type,
            "default": str(default) if default is not None else "",
            "required": i < pad,
        })

    has_kwargs = argspec.varkw is not None
    return params, has_kwargs


def _build_endpoint_html(path, route_info):
    """Build HTML for a single endpoint card."""
    func, argspec, auth, opts = route_info
    func_name = f"{func.__module__}.{func.__name__}"
    params, has_kwargs = _get_param_info(argspec)
    doc = inspect.getdoc(func) or ""
    requires_auth = "Yes" if auth else "No"
    safe_id = path.replace("/", "_").replace(".", "_")

    # Parameter rows
    param_rows = ""
    for p in params:
        req_badge = '<span class="badge req">required</span>' if p["required"] else '<span class="badge opt">optional</span>'
        param_rows += f"""
        <tr>
            <td><code>{p["name"]}</code></td>
            <td>{p["type"]}</td>
            <td>{p["default"]}</td>
            <td>{req_badge}</td>
            <td><input type="text" class="param-input" data-name="{p["name"]}" placeholder="{p["default"] or p["name"]}" /></td>
        </tr>"""

    if has_kwargs:
        param_rows += """
        <tr>
            <td colspan="5" class="kwargs-note">Accepts additional keyword parameters (**kwargs)</td>
        </tr>"""

    params_section = ""
    if param_rows:
        params_section = f"""
        <div class="params-section">
            <h4>Parameters</h4>
            <table class="params-table">
                <tr><th>Name</th><th>Type</th><th>Default</th><th>Required</th><th>Value</th></tr>
                {param_rows}
            </table>
        </div>"""

    return f"""
    <div class="endpoint" id="ep{safe_id}">
        <div class="endpoint-header" onclick="toggleEndpoint('ep{safe_id}')">
            <span class="method-badge get">GET</span>
            <span class="method-badge post">POST</span>
            <span class="endpoint-path">{path}</span>
            <span class="endpoint-func">{func_name}</span>
            <span class="auth-indicator {'auth-yes' if auth else 'auth-no'}">{'🔒' if auth else '🔓'}</span>
            <span class="chevron">▶</span>
        </div>
        <div class="endpoint-body" style="display:none;">
            <div class="endpoint-meta">
                <p><strong>Function:</strong> <code>{func_name}</code></p>
                {"<p><strong>Description:</strong> " + doc + "</p>" if doc else ""}
                <p><strong>Auth Required:</strong> {requires_auth}</p>
            </div>
            {params_section}
            <div class="tryout-section">
                <h4>Try It Out</h4>
                <div class="tryout-controls">
                    <label>Method:
                        <select class="method-select">
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                        </select>
                    </label>
                    <label>Auth Key (APK):
                        <input type="text" class="auth-input" placeholder="Enter API key" />
                    </label>
                    <button class="btn-try" onclick="tryEndpoint('{path}', 'ep{safe_id}')">Execute</button>
                </div>
                <div class="response-section" style="display:none;">
                    <h4>Response</h4>
                    <div class="response-status"></div>
                    <pre class="response-body"></pre>
                </div>
            </div>
        </div>
    </div>"""


def generate_docs(routes, app_name="", version=""):
    """Generate the full Swagger-like HTML page. Returns cached version if routes haven't changed."""
    current_hash = _get_routes_hash(routes)
    if _cache["html"] and _cache["hash"] == current_hash:
        return _cache["html"]

    endpoints_html = ""
    for path in sorted(routes.keys()):
        endpoints_html += _build_endpoint_html(path, routes[path])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{app_name or 'MangoREST'} API Documentation</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fafafa; color: #3b4151; }}
    .topbar {{ background: #1b1b1b; padding: 12px 24px; display: flex; align-items: center; gap: 16px; }}
    .topbar h1 {{ color: #fff; font-size: 18px; font-weight: 600; }}
    .topbar .version {{ background: #49cc90; color: #fff; padding: 2px 10px; border-radius: 12px; font-size: 13px; }}
    .info-bar {{ background: #fff; border-bottom: 1px solid #e0e0e0; padding: 20px 24px; }}
    .info-bar .title {{ font-size: 28px; font-weight: 700; color: #3b4151; }}
    .info-bar .subtitle {{ color: #6b7280; margin-top: 4px; }}
    .info-bar .stats {{ margin-top: 10px; display: flex; gap: 20px; }}
    .info-bar .stat {{ background: #f0f0f0; padding: 6px 14px; border-radius: 6px; font-size: 13px; }}
    .container {{ max-width: 1200px; margin: 20px auto; padding: 0 24px; }}
    .global-auth {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }}
    .global-auth label {{ font-weight: 600; white-space: nowrap; }}
    .global-auth input {{ flex: 1; padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px; }}
    .global-auth .btn-auth {{ background: #49cc90; color: #fff; border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer; font-weight: 600; }}
    .global-auth .btn-auth:hover {{ background: #3bb578; }}
    .endpoint {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 8px; overflow: hidden; }}
    .endpoint-header {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; cursor: pointer; user-select: none; }}
    .endpoint-header:hover {{ background: #f8f8f8; }}
    .method-badge {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; color: #fff; text-transform: uppercase; }}
    .method-badge.get {{ background: #61affe; }}
    .method-badge.post {{ background: #49cc90; }}
    .endpoint-path {{ font-weight: 600; font-size: 15px; font-family: monospace; flex: 1; }}
    .endpoint-func {{ color: #8a8a8a; font-size: 12px; }}
    .auth-indicator {{ font-size: 16px; }}
    .chevron {{ color: #8a8a8a; transition: transform 0.2s; font-size: 12px; }}
    .endpoint.open .chevron {{ transform: rotate(90deg); }}
    .endpoint-body {{ padding: 16px 20px; border-top: 1px solid #e8e8e8; background: #fafafa; }}
    .endpoint-meta p {{ margin: 4px 0; font-size: 14px; }}
    .endpoint-meta code {{ background: #e8e8e8; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
    .params-section {{ margin-top: 16px; }}
    .params-section h4 {{ margin-bottom: 8px; font-size: 14px; color: #3b4151; }}
    .params-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .params-table th {{ background: #f0f0f0; text-align: left; padding: 8px 10px; border: 1px solid #e0e0e0; }}
    .params-table td {{ padding: 8px 10px; border: 1px solid #e0e0e0; }}
    .params-table code {{ background: #e8e8e8; padding: 1px 5px; border-radius: 3px; }}
    .param-input {{ width: 100%; padding: 6px 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; }}
    .badge {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
    .badge.req {{ background: #ff6b6b; color: #fff; }}
    .badge.opt {{ background: #e0e0e0; color: #555; }}
    .kwargs-note {{ font-style: italic; color: #888; font-size: 12px; }}
    .tryout-section {{ margin-top: 16px; border-top: 1px solid #e0e0e0; padding-top: 12px; }}
    .tryout-section h4 {{ margin-bottom: 8px; font-size: 14px; }}
    .tryout-controls {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
    .tryout-controls label {{ font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; }}
    .tryout-controls select, .tryout-controls input {{ padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; }}
    .btn-try {{ background: #4990e2; color: #fff; border: none; padding: 8px 24px; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 14px; }}
    .btn-try:hover {{ background: #357abd; }}
    .response-section {{ margin-top: 12px; }}
    .response-status {{ font-weight: 600; margin-bottom: 6px; font-size: 14px; }}
    .response-status.ok {{ color: #49cc90; }}
    .response-status.err {{ color: #f93e3e; }}
    .response-body {{ background: #1b1b1b; color: #d4d4d4; padding: 16px; border-radius: 6px; font-size: 13px; max-height: 400px; overflow: auto; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<div class="topbar">
    <h1>🥭 {app_name or 'MangoREST'}</h1>
    <span class="version">v{version}</span>
</div>
<div class="info-bar">
    <div class="title">{app_name or 'MangoREST'} API Documentation</div>
    <div class="subtitle">Interactive API explorer — expand endpoints, fill parameters, and test live.</div>
    <div class="stats">
        <span class="stat">📡 {len(routes)} endpoints</span>
        <span class="stat">🔒 {sum(1 for v in routes.values() if v[2])} require auth</span>
        <span class="stat">🔓 {sum(1 for v in routes.values() if not v[2])} open</span>
    </div>
</div>
<div class="container">
    <div class="global-auth">
        <label>🔑 Global API Key (APK):</label>
        <input type="text" id="globalAPK" placeholder="Enter your API key here — applies to all requests" />
        <button class="btn-auth" onclick="document.querySelectorAll('.auth-input').forEach(i=>i.value=document.getElementById('globalAPK').value)">Apply to All</button>
    </div>
    {endpoints_html}
</div>
<script>
function toggleEndpoint(id) {{
    const el = document.getElementById(id);
    const body = el.querySelector('.endpoint-body');
    el.classList.toggle('open');
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
}}

function tryEndpoint(path, epId) {{
    const ep = document.getElementById(epId);
    const method = ep.querySelector('.method-select').value;
    const authKey = ep.querySelector('.auth-input').value || document.getElementById('globalAPK').value;
    const inputs = ep.querySelectorAll('.param-input');
    const resSection = ep.querySelector('.response-section');
    const resStatus = ep.querySelector('.response-status');
    const resBody = ep.querySelector('.response-body');

    const params = new URLSearchParams();
    inputs.forEach(inp => {{
        if (inp.value) params.append(inp.dataset.name, inp.value);
    }});

    let url = path;
    const opts = {{ method: method, headers: {{}} }};
    if (authKey) opts.headers['APK'] = authKey;

    if (method === 'GET') {{
        const qs = params.toString();
        if (qs) url += '?' + qs;
    }} else {{
        opts.body = params;
        opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }}

    resSection.style.display = 'block';
    resStatus.textContent = 'Loading...';
    resStatus.className = 'response-status';
    resBody.textContent = '';

    fetch(url, opts)
        .then(async resp => {{
            const text = await resp.text();
            resStatus.textContent = resp.status + ' ' + resp.statusText;
            resStatus.className = 'response-status ' + (resp.ok ? 'ok' : 'err');
            try {{ resBody.textContent = JSON.stringify(JSON.parse(text), null, 2); }}
            catch {{ resBody.textContent = text; }}
        }})
        .catch(err => {{
            resStatus.textContent = 'Error';
            resStatus.className = 'response-status err';
            resBody.textContent = err.toString();
        }});
}}
</script>
</body>
</html>"""

    _cache["html"] = html
    _cache["hash"] = current_hash
    return html
