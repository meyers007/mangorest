#!/usr/local/bin/python
'''
Directory Listing Service
'''
import os, sys, datetime, re, json, importlib, glob
from django.http import HttpResponse, JsonResponse,FileResponse
import mangorest.mango
from   mangorest.mango import webapi
import mimetypes

base = "/opt/data/ANALYSIS/data"

@webapi("/data")
def dirlist(**kwargs):
    
    if (kwargs.get("file" , None)):
        f = kwargs.get("file")
        if ( not os.path.isfile(f) ):  
            return f"{f} is not a file"
        
        response = FileResponse(open(f, 'rb'))
        ct = list(response._headers['content-type'])
        #print(f" ==> {vars(response)} {ct}") 
        if ( ct[1] == "text/csv"):
            ct[1] = "text/html"
            
        #print(f" ==> {response.headers['Content-Type']} ") 
        return response
        
    dirs= kwargs.get("base" , f"{base}/*")
    req = kwargs.get("request", None)
    url = (req and req.build_absolute_uri()) or "http://localhost:80/data/"
    url = url.split('?')[0].strip('/')
    
    print(f"===>  {dirs} {url}")
    if ( os.path.isdir(dirs)):
        dirs = dirs + "/**"
        
    fil = glob.glob(f'{dirs}', recursive=True)
    
    ret = "".join([f'<li><a href={url}?file={f}>{url}?file={f}</a>' for f in fil])
    return f"<h1>Directory listing for: {base} </h1><br/>" + ret
