#!/usr/local/bin/python

# **** DO NOT EDIT THIS FILE => Generated from djangomin.ipynb***

import sys, os,datetime, inspect,hashlib, json, django
#from django.conf.urls import url
from django.urls import path, re_path
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.core.management import execute_from_command_line
import numpy as np
from proxy.views import proxy_view

'''
References: 
https://blog.miguelgrinberg.com/post/the-ultimate-guide-to-python-decorators-part-iii-decorators-with-arguments
https://simpleisbetterthancomplex.com/article/2017/08/07/a-minimal-django-application.html

'''

__VERSION__ = "1.14"
__NAME__    = ""
PORT        = 9000
#--------------------------------------------------------------------------------
def index(request):
        return showroutes(request)    
#--------------------------------------------------------------------------------
DEBUG=0
def logp(*args, **kwargs):
    if not DEBUG:
        return;
    
    for c in kwargs:
        print(kwargs[c], end=" ")
    for c in args:
        print(c, end=" ")
    print()
#--------------------------------------------------------------------------------
def Debug(request, APPNAME=''):
    rpath = request.path.split('/')[-2] #en(APPNAME)+2:-1]
    template = "/templates/" + rpath;
    pyModule = rpath;
    
    logp(f"{template} Requested")
    getlist = [ c for c in request.GET.items()]
    ret = f''' <pre>\n Response Object: \n{os.getcwd()} path_info:{request.path_info}: final:{rpath}
               Page exists:  {template} : {os.path.exists(template)}
               Page exists:  {pyModule} : {os.path.exists(pyModule)}
               {getlist} </pre> '''
    return HttpResponse(ret);
#--------------------------------------------------------------------------------
# ALL you need to do is just define a function as follows
# def test(a=n, **kwargs):
#    #do your stuff
#    return 
# This function will take care of the rest

class myEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.int64):
            return int(obj)
        else:
            return super(DjangoJSONEncoder, self).default(obj)

# --------------------------------------------------------------------------------
def getparms(request):
    par = {}
    for c in request.GET.keys():
        par[c] = request.GET.get(c)
    for c in request.POST.keys():
        par[c] = request.POST.get(c)

    return par;
# --------------------------------------------------------------------------------
def CallMethod(method, request, args=None):
    par = getparms(request)
    if(args is None):
        args = inspect.getfullargspec(method)
    if (args.varkw == None ):
        return method(request)

    par["request"] = request

    try:
        ret = method(**par)
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse(f"Error: {e}")

    if ('content_type' in par and par['content_type'] == 'json'):
        if (type(ret) == str):
            ret = json.loads(ret)
            
        return JsonResponse(ret, safe=False)

    if (isinstance(ret, django.http.response.HttpResponseBase) ):
        return ret;
    
    if (type(ret) != str):
        ret = json.dumps(ret, cls=myEncoder)
        
    return HttpResponse(ret) #, content_type="text/plain")
#--------------------------------------------------------------------------------
def TryRunPyMethod(request):
    rpaths = [c for c in request.path.split("/") if (c) ];
    pyMethod = rpaths[-1];

    if ( pyMethod.find("modules.") < 0 ):
        return HttpResponse(f"{pyMethod} not understood 0")
        
    spl = pyMethod.split('.');
 
    if ( len(spl) < 2):
        logp("Hmmm ... May be not what is intended!! module name")
        return HttpResponse(f"{pyMethod} not understood 2");
    
    modName = ".".join(spl[:-1])
    __import__(modName, fromlist="dummy")
    
    funName = spl[-1]
    for v in sys.modules:
        if (v.startswith(modName)):
            method= getattr(sys.modules[v], funName)
            logp("==>", v, type(v), funName, method, type(method), callable(method))
            return CallMethod(method, request)
        
    return HttpResponse(f"{pyMethod} not understood3 ");
    
#--------------------------------------------------------------------------------
'''
USE following methods to pass in AUTH Key:
    curl -i -H "APK: 123"  http://localhost:9000
'''
def AuthorizeAPIKEY(request):
    apk = request.headers.get("APK", "")
    apk = apk or request.GET.get("APK", "?")
    apk = apk or request.POST.get("APK", "")
    # print(f"====> FOUND {request.path} {apk} ++")
    # Validate APK Key and return "Eror Description"

#--------------------------------------------------------------------------------
@login_required(login_url='/accounts/login/')
def Authorize(request):
        return ""
#--------------------------------------------------------------------------------
EXP_SETTINGS = {}

@login_required(login_url='/accounts/login/')
def CommonSecured(request, apage):
    authError = Authorize(request)
    if (  authError ):
        return HttpResponse(f"{path} -- {authError}!!");
    
    return render(request, apage, EXP_SETTINGS )
#--------------------------------------------------------------------------------
def showroutes(request):
    ret = f'''
    <h1>{__NAME__} - Version {__VERSION__} </h1>
    
    <h3> Showing ALL ROUTES # of Routes: {len(_WEBAPI_ROUTES.keys())} </h3><br/>
    <table width=% border=1>
    <tr><th>Path</th><th>Function Entry Point</th><th>Args</th><th>Auth Key</th><th>Misc</th></tr>

    These are the REST end points you may use - please note the APKKEY requirements
    <br/>
    '''
    for k,v in _WEBAPI_ROUTES.items():
        f = v[0]
        fname = f'{f.__module__}.{f.__name__}'

        ret += f'<tr><td>{k}</td><td>{fname}</td><td>{v[1].args}</td><td>{v[2]}</td><td>{v[-1]}</td></tr>\n'

    ret += "</table>"
    return HttpResponse(ret)
#--------------------------------------------------------------------------------
def HandleProxy(request):
    url = request.GET.get("url", None)
    if (not url):
        url = request.POST.get("url", None)

    logp(f'*Proxy request: [{url}]')
    if (not url):
        return HttpResponse("NO URL Given")

    try:
        response = proxy_view(request, url)
    except Exception as e:
        response = f"ERROR: {url} {e}"
    return HttpResponse(response)

def Common(request):
    '''    if ( 'session' in request ):
            if ( not request.session.get("mango", None)):
                request.session["mango"] = {}
                request.session["mango"]["count"] = 0
            else:
                request.session["mango"]["count"] = request.session["mango"]["count"]  + 1
    '''
    path = request.path[:-1] if request.path.endswith("/") else request.path
    if ( path.endswith("favicon.ico")):
        return HttpResponse(f"{path}!!");
    
    # Next STEP 1: check with registered URLS
    logp(f'*Check: {path} registered URLS: {_WEBAPI_ROUTES.keys()}')
    
    if (path == "/SHOW_ROUTES" ):
        return showroutes(request)
    
    if (path in _WEBAPI_ROUTES.keys() ):
        f, args, auth, opts = _WEBAPI_ROUTES[path]
        if ( auth ):
            ret = auth(request)
            if ( ret ):
                return HttpResponse(f"{path} -- {ret}!!");
        return CallMethod(f,request, args)

    # If not in the registered do templates:
    rpaths = [c for c in path.split("/") if (c)];
    if (len(rpaths) < 1):
        return index(request)

    # Check if it is a proxy request and we have proxy registered
    if rpaths[0] == "proxy":
        return HandleProxy(request)

    # Check for Templates
    template = f"{rpaths[0]}/templates/{'/'.join(rpaths[1:])}";
    rpath    = "/".join(rpaths[1:]);
    
    logp(rpaths, f'=*=>{path} {template}; {rpaths} ++ {rpath}');

    if ( os.path.exists(template) and request.path.find("/secured/") > 0) : 
        logp("Secured ==> " , rpaths, "==>", template);
        return CommonSecured(request, rpath)
    elif ( os.path.exists(template) ):
        #return render(request, rpath, settingsMAP())
        return render(request, rpath, EXP_SETTINGS )
    elif rpaths[-1].find("modules.") >= 0: #Must be a python module call
        logp("**** Getting python Module")
        return TryRunPyMethod(request)
    
    return HttpResponse(f"{path} not understood");
    
#--------------------------------------------------------------------------------
_WEBAPI_ROUTES={}
def webapi(url, auth=None, **kwargs):
    if auth and not inspect.isfunction(auth):
        auth = AuthorizeAPIKEY
        
    if type(url) is not str:
        f = url
        url = f'/{f.__module__}.{f.__name__}'
        m = inspect.getfullargspec(f)
        print(f"Registering url: {url} {f} {type(url)}")
        _WEBAPI_ROUTES[url] = [f, m, auth, kwargs]
        
        return f
    
    def inner_decorator(f):
        if url in _WEBAPI_ROUTES:
            print(f"Warning: Duplicate registration: {url} ")

        m = inspect.getfullargspec(f)
        url1 = url if url.startswith("/") else "/"+url
        url1 = url1[:-1] if url1.endswith("/") else url1
        
        _WEBAPI_ROUTES[url1] = [f, m, auth, kwargs]

        return f

    return inner_decorator
#----------------------------------------------------------------------------------
def inJupyter():
    try:    get_ipython; return True
    except: return False
#--------------------------------------------------------------------------------
SECRET        = f'{os.name}{os.getcwd()}{datetime.datetime.now()}'
DEBUG         = True
SECRET_KEY    = hashlib.sha224(bytes(SECRET, 'utf-8')).hexdigest()
ALLOWED_HOSTS = ['*']
#--------------------------------------------------------------------------------
def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', __file__)
    settings.configure(
        DEBUG=DEBUG,
        SECRET_KEY=SECRET_KEY,
        ROOT_URLCONF=__name__,
        BASE_DIR=os.getcwd(),
        ALLOWED_HOSTS=ALLOWED_HOSTS,
        CORS_ORIGIN_ALLOW_ALL=True,
        CSRF_COOKIE_HTTPONLY=False,
        CSRF_COOKIE_SECURE=False,
        AUTHORIZE="",  # Can be a Function, method,
        MIDDLEWARE=['corsheaders.middleware.CorsMiddleware',
                    # "django.middleware.csrf.CsrfViewMiddleware"
                    ],
        MIDDLEWARE_CLASSES=(
            'django.middleware.common.CommonMiddleware',
        ),
    )
    #EXP_SETTINGS = {a: getattr(settings, a) for a in dir(settings) if a.startswith('EXP_')};
    argv = [c for c in sys.argv]
    if len(argv) <= 1:
        print(f"** NOTICE ***\n\nTry running: {sys.argv[0]} runserver 0:9000 #to run on port 9000\n***\n")
        argv.extend(["runserver", f"0:{PORT}"])
    execute_from_command_line(argv)

urlpatterns = (
    re_path(r'^.*', Common, name='catchall'),
)
    
if __name__ == '__main__' and not inJupyter():
    main()
    pass
