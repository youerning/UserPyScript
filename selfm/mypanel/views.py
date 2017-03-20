# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from horizon import views
from openstack_dashboard import api
import datetime
from utils import ceil
import json  
from django.http import HttpResponse  



def lastDate(now, last=1):
    """get the last date ,by default the date range is 1 days"""
    lastTime = now - datetime.timedelta(days=last)
    now = now.isoformat()
    lastTime = lastTime.isoformat()    

    return (now, lastTime)

def ptime(dt):
    """parse the form time"""
    try:
        dt = datetime.datetime.strptime(dt,'%m/%d/%Y')
        ret = dt.isoformat()
    except Exception as e:
        print e        

    return ret

class IndexView(views.APIView):
    # A very simple class-based view...
    template_name = 'project/mypanel/index.html'

    def get_data(self, request, context, *args, **kwargs):
        # Add data to the context here...
        return context

    def get_context_data(self, **kwargs):
        """
        index => monitor index
        lastDate.l1,l7,l30 => last 1,7,30 days time range
        rg => timerange
        tl => till the end 
        fr => from  the begin
        host => the instance id
        hn => the instance display name
        """
        index = ["cpu", "mem", "disk", "net"]
        now = datetime.datetime.now()
        context = super(IndexView, self).get_context_data(**kwargs)
        instances, m = api.nova.server_list(self.request)
        insLis = [i.to_dict() for i in instances]
        insLis = [[i["id"],i["name"]] for i in insLis]

        lasttime = {}

        l1 = lastDate(now, 1)
        l7 = lastDate(now, 7)
        l30 = lastDate(now, 30)

        lasttime["l1"] = ["l1", l1, 1]
        lasttime["l7"] = ["l7", l7, 7]
        lasttime["l30"] = ["l30", l30, 30]
        rg = "l1"
        tl = ""
        fr = ""

        if insLis:
            c = ceil(insLis[0][0], l1)
            context["host"] = insLis[0][0]
            context["hn"] = insLis[0][1]
            ind = "CPU"
            ret = c.cpu()
        else:
            context["host"] = "no instance"
            context["hn"] =  "no instance"
            ind = "no instance"
            ret = ""
        
        
        context["ind"] =  ind
        context["ret"] = ret
        context["ins"] = insLis
        context["index"] = index
        context["lasttime"] = lasttime
        context["rg"] = rg
        context["tl"] = tl
        context["fr"] = fr
        return context

class HostView(views.APIView):
    # A very simple class-based view...
    template_name = 'project/mypanel/index.html'

    def get_data(self, request, context, *args, **kwargs):
        # Add data to the context here...
        return context

    def get_context_data(self, **kwargs):
        index = ["cpu", "mem", "disk", "net"]
        now = datetime.datetime.utcnow()
        context = super(HostView, self).get_context_data(**kwargs)
        hid = kwargs["hostid"]
        ind = self.request.GET.get("index").lower()
        hn = self.request.GET.get("hn")
        instances, m = api.nova.server_list(self.request)
        insLis = [i.to_dict() for i in instances]
        insLis = [[i["id"],i["name"]] for i in insLis]

        lasttime = {}

        l1 = lastDate(now, 1)
        l7 = lastDate(now, 7)
        l30 = lastDate(now, 30)

        lasttime["l1"] = ["l1", l1, 1]
        lasttime["l7"] = ["l7", l7, 7]
        lasttime["l30"] = ["l30", l30, 30]
        rg = ""
        tl = ""
        fr = ""


        if hn == "no instance":
            ret = ""
        
        elif self.request.GET.has_key("rg") and not self.request.GET.has_key("tl"):
            rg = self.request.GET.get("rg")
            lastd = lasttime[rg][1]
            #print lastd
            c = ceil(hid, lastd)
            indfuc = getattr(c, ind)
            ret = indfuc()
            
        elif self.request.GET.has_key("tl") and self.request.GET.has_key("fr"):
            tl = self.request.GET.get("tl")
            fr = self.request.GET.get("fr")
            tl1 = ptime(tl)
            fr1 = ptime(fr)
            c = ceil(hid, (tl1, fr1))
            indfuc = getattr(c, ind)
            ret = indfuc()
        else:
            c = ceil(hid, l1)
            indfuc = getattr(c, ind)
            ret = indfuc()
            rg = "l1"

        #print "====>", ret
        #print "====>", m
        
        context["host"] = hid
        context["hn"] = hn
        context["ind"] =  ind
        context["ret"] = ret
        context["ins"] = insLis
        context["index"] = index
        context["lasttime"] = lasttime
        context["rg"] = rg
        context["tl"] = tl
        context["fr"] = fr
        return context

def jsonp(request):
    ret = {"1":2,"data":[{"1":2,"ss":1,"ss":[1,2,3]}]}
    #print request.GET.has_key("111")

    return HttpResponse(json.dumps(ret), content_type="application/json") 
