'''
pip install mangorest
decorate function with @webapi -- best if your function takes kwargs as shown below

run oth.py

visit using your browser:
    http://localhost:9001/other2 OR
    http://localhost:9001/__main__.OtherTest1 OR
    
    
if you import this file then 
    http://localhost:9001/oth.OtherTest1 
'''

import mangorest
from  mangorest import webapi

@webapi
def OtherTest1(h='test1', **kwargs):
    ret = (f"Hello OtherTest1 {h} {kwargs}")
    print(ret)
    return ret
 
@webapi("/other2")
def OtherTest2(**kwargs):
    ret = (f"Hello OtherTest2 {kwargs}")
    print(ret)
    return ret


mangorest.__VERSION__ = "1.1"
mangorest.PORT        = 9001
if __name__ == '__main__' and not mangorest.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest._WEBAPI_ROUTES.keys()}')
    mangorest.main()
    pass    
