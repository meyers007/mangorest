#!/usr/local/bin/python
import mangorest
import oth
    
mangorest.__VERSION__ = "1.1"
mangorest.PORT        = 9000
if __name__ == '__main__' and not mangorest.inJupyter():
    print(f'** NOTICE *** registered URLS: {mangorest._WEBAPI_ROUTES.keys()}')
    mangorest.main()
    pass    
