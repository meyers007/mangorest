#!/usr/local/bin/python
import mangorest.mango
import myfile
    
mangorest.mango.__VERSION__ = "1.1"
mangorest.mango.PORT        = 9000
if __name__ == '__main__' and not mangorest.mango.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest.mango._WEBAPI_ROUTES.keys()}')
    mangorest.mango.main()
    pass    
