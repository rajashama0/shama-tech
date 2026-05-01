
import json
from bson import ObjectId

# improving JSONEncoder to be able to convert dictionaries with object id to json string
# how to use  "from DictToJson import converter"
# json_str = convert(dict)
#

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


def obj2str(dict):
    json_data = json.dumps(dict, cls=JSONEncoder)
    return json_data
    
        
#
#b
#{'100': {'id': 100, 'name': 'a'}, '200': {'id': 100, 'name': 'a'}, '04': {'id': 100, 'name': 'a'}}
#>>>
# >>> sorted(b)
#['04', '100', '200']
#>>> b
#

def vec2global(vec,id="id",issorted=True):
    ans={}
    for e in vec:
        id1=e[id]
        ans[id1]=e
    #if issorted:
    #    ans=sorted(ans, key=lambda x:x[0])
    return ans

def global2vec(gl,id="id"):
    vec=[]
    for k,v in gl.items():
        v["id"]=k
        vec.append(v)
    return vec


if False:
	print(obj2str({"eli":100}))    
	obj={"user":"eli","phone":"09999999"}
	print(obj2str({"eli-eli_eli eli אלי":[100,200],"obj":obj}))
	print(obj2str({"eli":'100 \" \'  '}))    
