# Deploy Sophisticated Python Django Webservice  in Less Than a Minute

## What is this about?  

Create Web service in less than a minute for any python function

It is about very minmal and quick way to deploy web services super fast; yet again have very robust control if needed;

* In future, it will extend extensive security control that can be implemented if needed
* Support for authoriation and authentication
* Support very sophiscated control 
* Support WSGI standards

## How to use it

See Examples in test directory here: https://github.com/meyers007/mangorest/blob/master/test/oth.py

STEP 1.

```
pip install Django, serializers, mangorest
```

STEP 2: decorate your functions with @webapi - see example below
(Please use kwargs for your own sanity)

```
#---- myfile.py----

from  mangorest import webapi

@webapi
def ws1(h='param1', **kwargs):
    ret = (f"Web Service {h} {kwargs}")
    return ret

@webapi("/ws2")
def ws2(**kwargs):
    ret = (f"Web service 2 {kwargs}")
    return ret
```


STEP 3: import myfile ex: absmin.py- for ex:

```
#---- myfile.py----

import mangorest
import myfile
    
mangorest.__VERSION__ = "1.1"
mangorest.PORT        = 9000
if __name__ == '__main__' and not mangorest.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest._WEBAPI_ROUTES.keys()}')
    mangorest.main()
    pass    
```


STEP 4: run 

```
python myfile 
```

STEP 5: finally visit http://localhost:9000 OR http://localhost:9000/ws1?h=wan OR http://localhost:9000/ws2 

**THAT IS ALL**

With little more effort, you can 

* deploy it on gunicorn, 
* secure it, 
* deploy it on cloud or open shift, 
* collect statistics
* autorize with APK tokents and issue to throttle the requests
* Many more and best of all, you can extend it beyond


# Apache License 
