#!/usr/local/bin/python
import mangorest.mango
from   mangorest.mango import webapi

@webapi
def test1(h='test1', **kwargs):
    ret = (f"Hello Test1 {h} {kwargs}")
    print(ret)
    return ret

@webapi("/app1/testingroot2/")
def test2(request, h="test2", **kwargs):
    ret = (f"Hello Test2 {h} {kwargs} {request.headers}")
    ret = (f"Hello Test2 {h} {kwargs}")

    print(ret)
    return ret

mangorest.mango.__VERSION__ = "1.1"
mangorest.mango.PORT        = 9050
if __name__ == '__main__' and not mangorest.mango.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest.mango._WEBAPI_ROUTES.keys()}')
    mangorest.mango.main()
    pass
