# Deploy Python Django Webservice  in Less Than a Minute

## What is this about?  

Create Web service in less than a minute for any python function

It is about very minimal and quick way to deploy web services super fast; yet again have very robust control if needed;

* In future, it will extend extensive security control that can be implemented if needed
* Support for authoriation and authentication


## How to use it

See Examples in test directory here: https://github.com/meyers007/mangorest/blob/master/test/oth.py


STEP 1.
```
pip install django serializers mangorest
```

STEP 2: decorate your functions with @webapi - see example below
(Please use kwargs for your own sanity)

```
#---- myfile.py----
from  mangorest.mango import webapi

@webapi("/ws2")
def ws2(**kwargs):
    ret = (f"Web service 2 {kwargs}")
    return ret
    
```


STEP 3: import myfile in another file ex: simple.py - for ex:

```
import mangorest.mango
import myfile
    
mangorest.mango.__VERSION__ = "1.1"
mangorest.mango.PORT        = 8050
if __name__ == '__main__' and not mangorest.mango.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest.mango._WEBAPI_ROUTES.keys()}')
    mangorest.mango.main()
    pass    
```

STEP 4: run 

```
python simple.py runserver 0:8050
```

STEP 5: finally visit http://localhost:8050 OR http://localhost:8050/ws2?h=tan OR http://localhost:8050/ws2 

**THAT IS ALL**

#### OPTIONAL STEP 0:
I assume that you have two python environments and be sure create an environment right for your purpose.
(1) /usr/bin/python3 ==> 3.8.9 version
(2) /usr/local/bin/python3 ==> 3.8.3 version

```
mkdir ~/venvs
cd ~/venvs
EXPORT PYENV=/usr/local/bin/python
EXPORT PYENV=/usr/bin/python3

python3.13 -m venv .venv

source .venv/bin/activate


```

## Why?

I write a lot of python code that needs to be deployed juts by tagging it with @webapi.
There is nothing more to do. The framework automatically sends in the argumens in kwargs.

There is no need to import any HTTP request objects or parse through them.
I wanted my functions to be used in regular python and tested - at the same time become a web service.


## @webapi Decorator Parameters

The `@webapi` decorator registers a function as an API endpoint. It accepts these parameters:

```python
@webapi(url, auth=None, **kwargs)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | (required) | The URL path for the endpoint, e.g. `"/app1/test"` |
| `auth` | function/bool | `None` | Set to `True` to require API key auth, or pass a custom auth function |
| `doc` | str | `""` | Short description shown in API docs summary |
| `version` | str | `""` | Version label for this endpoint |
| `files` | bool | `False` | Set to `True` to enable file upload in the API docs UI |
| `mcp` | bool | `False` | Flag for MCP-enabled endpoints |
| `**kwargs` | any | | Any extra keyword args are stored and displayed as metadata badges in the docs |

### Examples

```python
from mangorest.mango import webapi

# Simple endpoint
@webapi("/app1/test")
def test(request, **kwargs):
    return "Hello"

# Endpoint with documentation, version, and auth
@webapi("/app1/data", doc="Fetch data records", version="2.0", auth=True)
def get_data(request, param1="default", param2="value", **kwargs):
    '''
    Fetch data records from the database.
    Supports filtering by param1 and param2.
    '''
    return {"param1": param1, "param2": param2}

# Endpoint that accepts file uploads
@webapi("/app1/upload", files=True, doc="Upload a file")
def upload(request, **kwargs):
    for f in request.FILES.getlist('file'):
        content = f.read()
    return "Uploaded"
```

**Note:** The `request` parameter is automatically injected by the framework — it is excluded from the API docs UI. Only your custom parameters (e.g. `param1`, `param2`) are shown.


## MANGO_SETTINGS (Django Settings)

When using MangoREST inside a Django project, you can customize the API documentation page by adding `MANGO_SETTINGS` to your `settings.py`:

```python
# settings.py

MANGO_SETTINGS = {
    "TITLE": "My App API",
    "DESCRIPTION": "REST API for My Application.",
    "VERSION": "2.0.0",
    "APK_KEY_STORE": "",
}
```

### Default Values

If `MANGO_SETTINGS` is not defined, or if any key is missing, these defaults are used:

| Key | Default | Description |
|-----|---------|-------------|
| `TITLE` | `"API Documentation"` | Page title and heading |
| `DESCRIPTION` | `"API for managing this app."` | Subtitle shown below the title |
| `VERSION` | `"1.0.0"` | Version badge in the topbar |
| `APK_KEY_STORE` | `""` | API key store reference (reserved) |


## API Documentation UI

MangoREST auto-generates a Swagger-like interactive API documentation page at `/apis/doc`.

Features:
* **Interactive Try It Out** — fill parameters and execute requests live
* **File upload support** — for endpoints with `files=True`
* **Authorization modal** — supports Basic Auth (username/password) and Cookie/Token/APK key auth
* **Save credentials** — optionally save auth to browser cookies for persistence
* **Auto-generated from code** — reads function signatures, docstrings, and `@webapi` kwargs
* **Cached** — HTML is regenerated only when routes or settings change


## Roadmap

With little more effort, you can - I will add these 

* deploy it on gunicorn, 
* secure it, 
* deploy it on cloud or open shift, 
* collect statistics
* autorize with APK tokents and issue to throttle the requests
* Many more and best of all, you can extend it beyond


# Apache License 
