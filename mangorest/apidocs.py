"""
Swagger-like API Documentation Generator for MangoREST.
Generates a cached, interactive HTML page from registered routes.
"""
import json
import hashlib
import inspect

try:
    from django.conf import settings as django_settings
except ImportError:
    django_settings = None

_MANGO_DEFAULTS = {
    "TITLE": "API Documentation",
    "DESCRIPTION": "API for managing this app.",
    "VERSION": "1.0.0",
    "APK_KEY_STORE": "",
}

def _get_mango_settings():
    """Read MANGO_SETTINGS from Django settings, falling back to defaults."""
    cfg = dict(_MANGO_DEFAULTS)
    if django_settings:
        user_cfg = getattr(django_settings, "MANGO_SETTINGS", {})
        cfg.update(user_cfg)
    return cfg

_cache = {"html": None, "hash": None, "cfg_hash": None}


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
    docstring = inspect.getdoc(func) or ""
    summary = opts.get("doc", "") or docstring.split("\n")[0] if docstring else ""
    requires_auth = "Yes" if auth else "No"
    ep_version = opts.get("version", "")
    accepts_files = opts.get("files", False)
    safe_id = path.replace("/", "_").replace(".", "_")

    # Build extra attributes from webapi kwargs
    extra_attrs = {k: v for k, v in opts.items() if k not in ("doc",)}
    attrs_html = ""
    if extra_attrs:
        attrs_html = '<div class="endpoint-attrs">'
        for k, v in extra_attrs.items():
            attrs_html += f'<span class="attr-badge"><strong>{k}:</strong> {v}</span>'
        attrs_html += '</div>'

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

    # kwargs row for additional params
    kwargs_input = ""
    if has_kwargs:
        kwargs_input = """
        <tr>
            <td colspan="5" class="kwargs-note">
                <strong>Additional parameters</strong> (name=value, one per line):<br/>
                <textarea class="kwargs-input" rows="2" placeholder="key1=value1&#10;key2=value2" style="width:100%;margin-top:4px;padding:6px 8px;border:1px solid #d0d0d0;border-radius:4px;font-size:13px;font-family:monospace;"></textarea>
            </td>
        </tr>"""

    params_table = ""
    if param_rows or kwargs_input:
        params_table = f"""
            <table class="params-table">
                <tr><th>Name</th><th>Type</th><th>Default</th><th>Required</th><th>Value</th></tr>
                {param_rows}
                {kwargs_input}
            </table>"""

    file_upload = ""
    if accepts_files:
        file_upload = """
                <div class="file-upload-section" style="margin-top:10px;">
                    <label style="font-weight:600;font-size:13px;">📁 Upload Files:</label>
                    <input type="file" class="file-input" multiple style="margin-left:8px;font-size:13px;" />
                </div>"""

    return f"""
    <div class="endpoint" id="ep{safe_id}">
        <div class="endpoint-header" onclick="toggleEndpoint('ep{safe_id}')">
            <span class="method-badge get">GET</span>
            <span class="method-badge post">POST</span>
            <span class="endpoint-path">{path}</span>
            <span class="endpoint-summary">{summary}</span>
            <span class="endpoint-func">{func_name}</span>
            <span class="auth-indicator {'auth-yes' if auth else 'auth-no'}">{'🔒' if auth else '🔓'}</span>
            <span class="chevron">▶</span>
        </div>
        <div class="endpoint-body" style="display:none;">
            <div class="endpoint-meta">
                <p><strong>Function:</strong> <code>{func_name}</code></p>
                {"<p><strong>Description:</strong> " + docstring.replace(chr(10), '<br/>') + "</p>" if docstring else ""}
                <p><strong>Auth Required:</strong> {requires_auth}</p>
                {attrs_html}
            </div>
            <div class="tryout-section">
                <h4>Try It Out</h4>
                {params_table}
                {file_upload}
                <div class="tryout-controls" style="margin-top:10px;">
                    <label>Method:
                        <select class="method-select">
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                        </select>
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
    cfg = _get_mango_settings()
    current_hash = _get_routes_hash(routes)
    cfg_hash = hashlib.md5(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    if _cache["html"] and _cache["hash"] == current_hash and _cache["cfg_hash"] == cfg_hash:
        return _cache["html"]

    title = app_name or cfg["TITLE"]
    desc = cfg["DESCRIPTION"]
    ver = version or cfg["VERSION"]

    endpoints_html = "<br/><h2>API Endpoints:</h2>"
    for path in sorted(routes.keys()):
        endpoints_html += _build_endpoint_html(path, routes[path])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fafafa; color: #3b4151; }}
    .topbar {{ background: #1b1b1b; padding: 12px 24px; display: flex; align-items: center; gap: 16px; }}
    .topbar h1 {{ color: #fff; font-size: 18px; font-weight: 600; }}
    .topbar .version {{ background: #49cc90; color: #fff; padding: 2px 10px; border-radius: 12px; font-size: 13px; }}
    .home-link {{ color: #fff; text-decoration: none; font-size: 15px; padding: 4px 12px; border: 1px solid #555; border-radius: 4px; }}
    .home-link:hover {{ background: #333; }}
    .info-bar {{ background: #fff; border-bottom: 1px solid #e0e0e0; padding: 20px 24px; }}
    .info-bar .title {{ font-size: 28px; font-weight: 700; color: #3b4151; }}
    .info-bar .subtitle {{ color: #6b7280; margin-top: 4px; }}
    .info-bar .stats {{ margin-top: 10px; display: flex; gap: 20px; }}
    .info-bar .stat {{ background: #f0f0f0; padding: 6px 14px; border-radius: 6px; font-size: 13px; }}
    .container {{ max-width: 1200px; margin: 20px auto; padding: 0 24px; }}
    .global-auth {{ background: transparent; border: 0px solid #e0e0e0; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; }}
    .global-auth label {{ font-weight: 600; white-space: nowrap; }}
    .global-auth input, .global-auth select {{ padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px; }}
    .global-auth .btn-auth {{ background: #49cc90; color: #fff; border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer; font-weight: 600; }}
    .global-auth .btn-auth:hover {{ background: #3bb578; }}
    .auth-row {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }}
    .auth-row:last-child {{ margin-bottom: 0; }}
    .auth-header {{ display: flex; align-items: center; justify-content: flex-end; }}
    .btn-authorize {{ background: #49cc90; color: #fff; border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer; font-weight: 700; font-size: 14px; }}
    .btn-authorize:hover {{ background: #3bb578; }}
    .auth-body {{ display: none; padding-top: 12px; border-top: 1px solid #e0e0e0; margin-top: 12px; }}
    .endpoint {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 8px; overflow: hidden; }}
    .endpoint-header {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; cursor: pointer; user-select: none; }}
    .endpoint-header:hover {{ background: #f8f8f8; }}
    .method-badge {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; color: #fff; text-transform: uppercase; }}
    .method-badge.get {{ background: #61affe; }}
    .method-badge.post {{ background: #49cc90; }}
    .endpoint-path {{ font-weight: 600; font-size: 15px; font-family: monospace; flex: 1; }}
    .endpoint-func {{ color: #8a8a8a; font-size: 12px; }}
    .endpoint-summary {{ color: #555; font-size: 13px; font-style: italic; }}
    .endpoint-attrs {{ margin-top: 8px; display: flex; gap: 10px; flex-wrap: wrap; }}
    .attr-badge {{ background: #eef2ff; border: 1px solid #c7d2fe; padding: 3px 10px; border-radius: 4px; font-size: 12px; color: #4338ca; }}
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
    .response-body.json-ok {{ border-left: 4px solid #49cc90; }}
    .response-body.json-err {{ border-left: 4px solid #f93e3e; }}
</style>
</head>
<body>
<div class="topbar">
    <a href="/" class="home-link">🏠 Home</a>
    <h1>🥭 {title}</h1>
    <span class="version">v{ver}</span>
</div>
<div class="info-bar">
    <div class="title">{title}</div>
    <div class="subtitle">{desc}</div>
    <div class="stats">
        <span class="stat">📡 {len(routes)} endpoints</span>
        <span class="stat">🔒 {sum(1 for v in routes.values() if v[2])} require auth</span>
        <span class="stat">🔓 {sum(1 for v in routes.values() if not v[2])} open</span>
    </div>
</div>
<div class="container">
    <div class="auth-header"><button class="btn-authorize" onclick="toggleAuth(this)">Authorize</button></div>
    <div class="global-auth">
        <div class="auth-body">
            <div class="auth-row">
                <label>🔑 Auth Key:</label>
                <input type="text" id="globalAuthKey" placeholder="Cookie, Token, or APK key" style="flex:1;" />
            </div>
            <div class="auth-row">
                <label>👤 Username:</label>
                <input type="text" id="globalUser" placeholder="username" style="max-width:150px;" />
                <label>🔒 Password:</label>
                <input type="password" id="globalPass" placeholder="password" style="max-width:150px;" />
                <button class="btn-auth" onclick="applyGlobalAuth()">Apply to All</button>
            </div>
        </div>
    </div>
    {endpoints_html}
</div>
<script>
function toggleAuth(el) {{
    const authDiv = el.closest('.auth-header').nextElementSibling;
    const body = authDiv.querySelector('.auth-body');
    const visible = body.style.display === 'block';
    body.style.display = visible ? 'none' : 'block';
}}

function toggleEndpoint(id) {{
    const el = document.getElementById(id);
    const body = el.querySelector('.endpoint-body');
    el.classList.toggle('open');
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
}}

function applyGlobalAuth() {{
    const key = document.getElementById('globalAuthKey').value;
    const user = document.getElementById('globalUser').value;
    const pass_ = document.getElementById('globalPass').value;
    // Store globally for tryEndpoint to pick up
    window._globalAuth = {{ key: key, user: user, pass: pass_ }};
}}

function tryEndpoint(path, epId) {{
    const ep = document.getElementById(epId);
    const method = ep.querySelector('.method-select').value;
    const gAuth = window._globalAuth || {{}};
    const authKey = gAuth.key || document.getElementById('globalAuthKey').value;
    const user = gAuth.user || document.getElementById('globalUser').value;
    const pass_ = gAuth.pass || document.getElementById('globalPass').value;

    // Collect named parameter inputs
    const inputs = ep.querySelectorAll('.param-input');
    const resSection = ep.querySelector('.response-section');
    const resStatus = ep.querySelector('.response-status');
    const resBody = ep.querySelector('.response-body');

    // Collect named params
    const params = {{}};
    inputs.forEach(inp => {{
        if (inp.value) params[inp.dataset.name] = inp.value;
    }});

    // Collect extra kwargs from textarea
    const kwArea = ep.querySelector('.kwargs-input');
    if (kwArea && kwArea.value.trim()) {{
        kwArea.value.trim().split(/\\\\r?\\\\n/).forEach(line => {{
            const eq = line.indexOf('=');
            if (eq > 0) params[line.substring(0, eq).trim()] = line.substring(eq + 1).trim();
        }});
    }}

    // Check for file uploads
    const fileInput = ep.querySelector('.file-input');
    const hasFiles = fileInput && fileInput.files.length > 0;

    let url = path;
    const opts = {{ method: method, headers: {{}} }};
    if (authKey) {{
        opts.headers['Cookie'] = authKey;
        opts.headers['Authorization'] = 'Token ' + authKey;
        opts.headers['APK'] = authKey;
    }}
    if (user && pass_) opts.headers['Authorization'] = 'Basic ' + btoa(user + ':' + pass_);

    if (method === 'GET') {{
        const qs = new URLSearchParams(params).toString();
        if (qs) url += '?' + qs;
    }} else if (hasFiles) {{
        const fd = new FormData();
        for (const [k, v] of Object.entries(params)) fd.append(k, v);
        for (const f of fileInput.files) fd.append('file', f);
        opts.body = fd;
        // Let browser set Content-Type with boundary
    }} else {{
        opts.body = new URLSearchParams(params);
        opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }}

    resSection.style.display = 'block';
    resStatus.textContent = 'Loading...';
    resStatus.className = 'response-status';
    resBody.textContent = '';
    resBody.classList.remove('json-ok', 'json-err');

    fetch(url, opts)
        .then(async resp => {{
            const text = await resp.text();
            const code = resp.status;
            resStatus.textContent = code + ' ' + resp.statusText;
            resStatus.className = 'response-status ' + (resp.ok ? 'ok' : 'err');
            try {{
                const obj = JSON.parse(text);
                resBody.textContent = JSON.stringify(obj, null, 2);
                resBody.classList.add(resp.ok ? 'json-ok' : 'json-err');
            }} catch {{
                resBody.textContent = text;
                if (!resp.ok) resBody.classList.add('json-err');
            }}
        }})
        .catch(err => {{
            resStatus.textContent = 'Network Error';
            resStatus.className = 'response-status err';
            resBody.textContent = err.toString();
            resBody.classList.add('json-err');
        }});
}}
</script>
</body>
</html>"""

    _cache["html"] = html
    _cache["hash"] = current_hash
    _cache["cfg_hash"] = cfg_hash
    return html
