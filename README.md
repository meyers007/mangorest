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
pip install Django, serializers, mangorest
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
mangorest.mango.PORT        = 9000
if __name__ == '__main__' and not mangorest.mango.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest.mango._WEBAPI_ROUTES.keys()}')
    mangorest.mango.main()
    pass    
```

STEP 4: run 

```
python simple.py
```

STEP 5: finally visit http://localhost:9000 OR http://localhost:9000/ws2?h=tan OR http://localhost:9000/ws2 

**THAT IS ALL**

## Why?

I write a lot of python code that needs to be deployed juts by tagging it with @webapi.
There is nothing more to do. The framework automatically sends in the argumens in kwargs.

There is no need to import any HTTP request objects or parse through them.
I wanted my functions to be used in regular python and tested - at the same time become a web service.


## Roadmap

With little more effort, you can - I will add these 

* deploy it on gunicorn, 
* secure it, 
* deploy it on cloud or open shift, 
* collect statistics
* autorize with APK tokents and issue to throttle the requests
* Many more and best of all, you can extend it beyond


# Apache License 
