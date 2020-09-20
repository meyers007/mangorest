from  mangorest import webapi

@webapi
def ws1(h='param1', **kwargs):
    ret = (f"Web Service {h} {kwargs}")
    return ret
 
@webapi("/ws2")
def ws2(**kwargs):
    ret = (f"Web service 2 {kwargs}")
    return ret
