#!/usr/local/bin/python
import mangorest
from   mangorest import webapi
import oth

@webapi
def test1(h='test1', **kwargs):
    ret = (f"Hello Test1 {h} {kwargs}")
    print(ret)
    return ret
    
@webapi("seattle_univ")
def test2(request, h="test2", **kwargs):
    ret = (f"Hello Test2 {h} {kwargs} {request.headers}")
    ret = (f"Hello Test2 {h} {kwargs}")
    
    print(ret)
    return ret
    
mangorest.__VERSION__ = "1.1"
mangorest.PORT        = 9001
if __name__ == '__main__' and not mangorest.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest._WEBAPI_ROUTES.keys()}')
    mangorest.main()
    pass    
