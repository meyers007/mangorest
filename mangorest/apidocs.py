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
    is_mcp = opts.get("mcp", False)
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

    mcp_badge = '<span class="mcp-badge">MCP</span>' if is_mcp else ''

    return f"""
    <div class="endpoint" id="ep{safe_id}" data-mcp="{'true' if is_mcp else 'false'}">
        <div class="endpoint-header" onclick="toggleEndpoint('ep{safe_id}')">
            <span class="method-badge get">GET</span>
            <span class="method-badge post">POST</span>
            {mcp_badge}
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

    mcp_count = sum(1 for v in routes.values() if v[3].get("mcp", False))

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
    .mcp-badge {{ background: #8b5cf6; color: #fff; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    .filter-bar {{ display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }}
    .filter-bar span {{ font-size: 13px; font-weight: 600; color: #555; }}
    .filter-btn {{ padding: 6px 16px; border: 1px solid #d0d0d0; border-radius: 20px; background: #fff; cursor: pointer; font-size: 13px; font-weight: 600; color: #555; }}
    .search-box {{ padding: 6px 14px; border: 1px solid #d0d0d0; border-radius: 20px; font-size: 13px; outline: none; width: 220px; margin-left: auto; }}
    .search-box:focus {{ border-color: #49cc90; box-shadow: 0 0 0 2px rgba(73,204,144,0.15); }}
    .filter-btn:hover {{ background: #f0f0f0; }}
    .filter-btn.active {{ background: #3b4151; color: #fff; border-color: #3b4151; }}
    .filter-btn.mcp-filter.active {{ background: #8b5cf6; border-color: #8b5cf6; }}
    .auth-header {{ display: flex; align-items: center; justify-content: flex-end; margin-bottom: 12px; }}
    .btn-authorize {{ background: #fff; color: #49cc90; border: 2px solid #49cc90; padding: 8px 24px; border-radius: 4px; cursor: pointer; font-weight: 700; font-size: 14px; }}
    .btn-authorize:hover {{ background: #f0fdf4; }}
    .btn-authorize.authed {{ background: #49cc90; color: #fff; }}
    /* Modal overlay */
    .auth-modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: flex-start; padding-top: 80px; }}
    .auth-modal-overlay.open {{ display: flex; }}
    .auth-modal {{ background: #fff; border-radius: 8px; width: 520px; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }}
    .auth-modal-header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid #e0e0e0; }}
    .auth-modal-header h2 {{ font-size: 18px; color: #3b4151; }}
    .auth-modal-close {{ background: none; border: none; font-size: 22px; cursor: pointer; color: #888; padding: 4px 8px; }}
    .auth-modal-close:hover {{ color: #333; }}
    .auth-modal-body {{ padding: 24px; }}
    .auth-section {{ border-bottom: 1px solid #e8e8e8; padding-bottom: 20px; margin-bottom: 20px; }}
    .auth-section:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
    .auth-section h3 {{ font-family: monospace; font-size: 16px; color: #3b4151; margin-bottom: 4px; }}
    .auth-section .auth-type {{ color: #6b7280; font-size: 13px; margin-bottom: 12px; }}
    .auth-section .auth-detail {{ color: #6b7280; font-size: 13px; margin-bottom: 2px; }}
    .auth-field {{ margin-bottom: 12px; }}
    .auth-field label {{ display: block; font-weight: 700; font-size: 13px; color: #3b4151; margin-bottom: 4px; }}
    .auth-field-wrap {{ display: flex; align-items: center; max-width: 380px; position: relative; }}
    .auth-field-wrap input {{ width: 100%; padding: 10px 40px 10px 12px; border: 2px solid #49cc90; border-radius: 4px; font-size: 14px; outline: none; }}
    .auth-field-wrap input:focus {{ border-color: #3bb578; box-shadow: 0 0 0 3px rgba(73,204,144,0.15); }}
    .eye-toggle {{ position: absolute; right: 8px; background: none; border: none; cursor: pointer; font-size: 18px; color: #888; padding: 2px 4px; }}
    .eye-toggle:hover {{ color: #3b4151; }}
    .auth-buttons {{ display: flex; gap: 10px; margin-top: 16px; }}
    .auth-btn-green {{ background: #fff; color: #49cc90; border: 2px solid #49cc90; padding: 8px 24px; border-radius: 4px; cursor: pointer; font-weight: 700; font-size: 14px; }}
    .auth-btn-green:hover {{ background: #f0fdf4; }}
    .auth-btn-gray {{ background: #fff; color: #666; border: 1px solid #ccc; padding: 8px 24px; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 14px; }}
    .auth-btn-gray:hover {{ background: #f5f5f5; }}
    .auth-btn-red {{ background: #fff; color: #f93e3e; border: 2px solid #f93e3e; padding: 8px 24px; border-radius: 4px; cursor: pointer; font-weight: 700; font-size: 14px; }}
    .auth-btn-red:hover {{ background: #fef2f2; }}
    .auth-save-row {{ display: flex; align-items: center; gap: 8px; margin-top: 10px; }}
    .auth-save-row label {{ font-size: 13px; color: #555; font-weight: 400; cursor: pointer; }}
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
    <a href="https://github.com/meyers007/mangorest.git" target="blank" class="home-link">⚙ GitHub</a>
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
        <span class="stat">🤖 {mcp_count} MCP tools</span>
    </div>
</div>
<div class="container">
    <div class="auth-header"><button class="btn-authorize" id="authOpenBtn" onclick="openAuthModal()">Authorize</button></div>

    <!-- Auth Modal -->
    <div class="auth-modal-overlay" id="authModal">
        <div class="auth-modal">
            <div class="auth-modal-header">
                <h2>Available authorizations</h2>
                <button class="auth-modal-close" onclick="closeAuthModal()">&times;</button>
            </div>
            <div class="auth-modal-body">
                <div class="auth-section">
                    <h3>basicAuth <span style="font-weight:400;color:#6b7280;">(http, Basic)</span></h3>
                    <div class="auth-field">
                        <label>Username:</label>
                        <div class="auth-field-wrap">
                            <input type="text" id="globalUser" placeholder="username" />
                        </div>
                    </div>
                    <div class="auth-field">
                        <label>Password:</label>
                        <div class="auth-field-wrap">
                            <input type="password" id="globalPass" placeholder="password" />
                            <button type="button" class="eye-toggle" onclick="toggleVis(this)">&#128065;</button>
                        </div>
                    </div>
                    <div class="auth-buttons">
                        <button class="auth-btn-green" onclick="authorizeBasic()">Authorize</button>
                        <button class="auth-btn-red" onclick="logoutBasic()" style="display:none;" id="logoutBasicBtn">Logout</button>
                    </div>
                </div>
                <div class="auth-section">
                    <h3>cookieAuth <span style="font-weight:400;color:#6b7280;">(apiKey)</span></h3>
                    <div class="auth-detail">Name: sessionid</div>
                    <div class="auth-detail" style="margin-bottom:10px;">In: cookie</div>
                    <div class="auth-field">
                        <label>Value:</label>
                        <div class="auth-field-wrap">
                            <input type="password" id="globalAuthKey" placeholder="session cookie or API key" />
                            <button type="button" class="eye-toggle" onclick="toggleVis(this)">&#128065;</button>
                        </div>
                    </div>
                    <div class="auth-buttons">
                        <button class="auth-btn-green" onclick="authorizeCookie()">Authorize</button>
                        <button class="auth-btn-red" onclick="logoutCookie()" style="display:none;" id="logoutCookieBtn">Logout</button>
                    </div>
                </div>
                <div class="auth-save-row">
                    <input type="checkbox" id="authSaveLocal" />
                    <label for="authSaveLocal">Save credentials locally (localStorage)</label>
                </div>
                <div class="auth-buttons" style="margin-top:16px; border-top:1px solid #e8e8e8; padding-top:16px;">
                    <button class="auth-btn-gray" onclick="closeAuthModal()">Close</button>
                </div>
            </div>
        </div>
    </div>
    <div class="filter-bar">
        <span>Filter:</span>
        <button class="filter-btn active" onclick="filterEndpoints('all', this)">All ({len(routes)})</button>
        <button class="filter-btn mcp-filter" onclick="filterEndpoints('mcp', this)">🤖 MCP ({mcp_count})</button>
        <button class="filter-btn" onclick="filterEndpoints('rest', this)">REST ({len(routes) - mcp_count})</button>
        <input type="text" class="search-box" id="endpointSearch" placeholder="🔍 Search endpoints..." oninput="searchEndpoints(this.value)" />
    </div>
    {endpoints_html}
</div>
<script>
function toggleVis(btn) {{
    const inp = btn.previousElementSibling;
    const isPass = inp.type === 'password';
    inp.type = isPass ? 'text' : 'password';
    btn.innerHTML = isPass ? '&#128064;' : '&#128065;';
}}

// Auth modal
function openAuthModal() {{
    document.getElementById('authModal').classList.add('open');
}}
function closeAuthModal() {{
    document.getElementById('authModal').classList.remove('open');
}}
// Close modal on overlay click
document.getElementById('authModal').addEventListener('click', function(e) {{
    if (e.target === this) closeAuthModal();
}});

function updateAuthBtn() {{
    const btn = document.getElementById('authOpenBtn');
    const g = window._globalAuth || {{}};
    const hasAuth = g.key || (g.user && g.pass);
    btn.classList.toggle('authed', !!hasAuth);
    btn.textContent = hasAuth ? '🔒 Authorized' : 'Authorize';
}}

function _saveAuthCookie() {{
    const data = JSON.stringify(window._globalAuth || {{}});
    const d = new Date(); d.setTime(d.getTime() + 30*24*60*60*1000);
    document.cookie = '_mangoAuth=' + encodeURIComponent(data) + ';expires=' + d.toUTCString() + ';path=/;SameSite=Lax';
}}
function _clearAuthCookie() {{
    document.cookie = '_mangoAuth=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;';
}}
function _loadAuthCookie() {{
    const match = document.cookie.match(/(?:^|;\s*)_mangoAuth=([^;]*)/);
    if (!match) return null;
    try {{ return JSON.parse(decodeURIComponent(match[1])); }} catch(e) {{ return null; }}
}}

function authorizeBasic() {{
    const user = document.getElementById('globalUser').value;
    const pass_ = document.getElementById('globalPass').value;
    if (!user || !pass_) return;
    window._globalAuth = window._globalAuth || {{}};
    window._globalAuth.user = user;
    window._globalAuth.pass = pass_;
    document.getElementById('logoutBasicBtn').style.display = 'inline-block';
    if (document.getElementById('authSaveLocal').checked) _saveAuthCookie();
    updateAuthBtn();
}}

function logoutBasic() {{
    document.getElementById('globalUser').value = '';
    document.getElementById('globalPass').value = '';
    if (window._globalAuth) {{ delete window._globalAuth.user; delete window._globalAuth.pass; }}
    document.getElementById('logoutBasicBtn').style.display = 'none';
    _clearAuthCookie();
    updateAuthBtn();
}}

function authorizeCookie() {{
    const key = document.getElementById('globalAuthKey').value;
    if (!key) return;
    window._globalAuth = window._globalAuth || {{}};
    window._globalAuth.key = key;
    document.getElementById('logoutCookieBtn').style.display = 'inline-block';
    if (document.getElementById('authSaveLocal').checked) _saveAuthCookie();
    updateAuthBtn();
}}

function logoutCookie() {{
    document.getElementById('globalAuthKey').value = '';
    if (window._globalAuth) delete window._globalAuth.key;
    document.getElementById('logoutCookieBtn').style.display = 'none';
    _clearAuthCookie();
    updateAuthBtn();
}}

// Load saved auth from cookie on page load
(function loadSavedAuth() {{
    try {{
        const saved = _loadAuthCookie();
        if (saved && Object.keys(saved).length) {{
            window._globalAuth = saved;
            if (saved.user) {{ document.getElementById('globalUser').value = saved.user; document.getElementById('logoutBasicBtn').style.display = 'inline-block'; }}
            if (saved.pass) document.getElementById('globalPass').value = saved.pass;
            if (saved.key) {{ document.getElementById('globalAuthKey').value = saved.key; document.getElementById('logoutCookieBtn').style.display = 'inline-block'; }}
            document.getElementById('authSaveLocal').checked = true;
            updateAuthBtn();
        }}
    }} catch(e) {{}}
}})();

function searchEndpoints(query) {{
    const q = query.toLowerCase().trim();
    document.querySelectorAll('.endpoint').forEach(ep => {{
        if (!q) {{ ep.style.display = ''; return; }}
        const path = ep.querySelector('.endpoint-path')?.textContent.toLowerCase() || '';
        const summary = ep.querySelector('.endpoint-summary')?.textContent.toLowerCase() || '';
        const func = ep.querySelector('.endpoint-func')?.textContent.toLowerCase() || '';
        ep.style.display = (path.includes(q) || summary.includes(q) || func.includes(q)) ? '' : 'none';
    }});
    // Reset filter buttons to 'All' active state
    document.querySelectorAll('.filter-btn').forEach((b, i) => b.classList.toggle('active', i === 0));
}}

function filterEndpoints(filter, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.endpoint').forEach(ep => {{
        const isMcp = ep.dataset.mcp === 'true';
        if (filter === 'all') ep.style.display = '';
        else if (filter === 'mcp') ep.style.display = isMcp ? '' : 'none';
        else ep.style.display = isMcp ? 'none' : '';
    }});
}}

function toggleEndpoint(id) {{
    const el = document.getElementById(id);
    const body = el.querySelector('.endpoint-body');
    el.classList.toggle('open');
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
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
