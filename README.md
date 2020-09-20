# Very Minimal Django Webservice Deployment 

## What is this about?  

It is about very minmal and quick way to deploy web services super fast; yet again have very robust control if needed;

* In future, it will extend extensive security control that can be implemented if needed
* Support for authoriation and authentication
* Support very sophiscated control 
* Support WSGI standards

## How to use it

```
pip install mangorest
```
TBD


## In your notebook

```
%reload_ext autoreload
%autoreload 2
import colabexts
from colabexts.jcommon import *

jpath=os.path.dirname(colabexts.__file__)
jcom = f'{jpath}/jcommon.ipynb'
%run $jcom

```


# Copyright 2020

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0


Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
