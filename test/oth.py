from mangorest.mango import webapi

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
