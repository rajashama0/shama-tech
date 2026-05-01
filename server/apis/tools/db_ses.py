import os, sys, uuid

sys.path.append(os.path.dirname(__file__))
from tools.sql  import *

#
#
# add2ses(ses, {"state":1})
#
#
# data ->    state = data["state"]
#
def add2ses(ses,obj):
    id=find_in_sql({'table':'ses','fld':'id','val':ses,'what':'id'})
    if id==False:
        return False
    for x in obj:
        add_to_data("ses",ses,x,obj[x])
        

def ses_list(r):
    # SELECT * FROM ses WHERE `is_active`=1 AND updated_at<DATE_SUB(NOW(),INTERVAL 24 HOUR)
    cond = f'updated_at<DATE_SUB(NOW(),INTERVAL {r["ttl"]} HOUR)'
    all=find_in_sql({'table':'ses','fld':'is_active','val':1,'all':1,'what':'*','where':cond})
    return all
    
    
def is_ses(ses):
    w=find_in_sql({'table':'ses','fld':'id','val':ses,'what':'id'})
    if type(w) is bool:
        return 0
    return 1



    
    
#
# api - check login
#
# called from api_login
#
def create_new_ses(uid):
    ses = uuid.uuid4().hex[0:29]
    res = insert_to_sql({'table':'ses','set':f"id='{ses}',user_id={uid}"})
    if res["status"]:
        return ses
    return 0
    
    
def check_ses(ses):
    w=find_in_sql({'table':'ses','fld':'id','val':ses,'what':'id'})
    if type(w) is bool:
        return 0
    return 1
    
    
def live_url(cont_id):
    w=find_in_sql({ 'table':'ses',
                    'where':f'data->"$.cont_id"="{cont_id}"',  # make sure all search inside data is string 
                    'fld':'is_active','val':2,
                    'what':'id','all':1 
    })
    
    s = w[0]
    
    url = f"/pages/renew.html?ses={s}&a=1&admi=1"
    return url
