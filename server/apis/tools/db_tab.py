# 
# 
# gen tables
#
#
from tools.sql import *


#
# return gen table as array
#
# ex: 
# status = get_tab_item("route_type")
#          pn", "residential_proxy"
# 
def list_gen_tab(tab):
    g = gen_data()
    obj = g[tab]["data"]
    return obj
    #
    #    list = list_gen_tab("enc_type")
    #    ['base64', 'AESGCM128bit'] 
    # 
    
    
    
    
#
# tables with field as a code (1,2..)
# the dictionary of this code 1:"opt1" 2:"opt2" ... 
#
#
#
def list_tab_dict(table,fld):
    g = gen_data()
    tab = f"{table}_dict"
    obj = g[tab]["data"]
    fld_obj = obj.get(fld)
    return fld_obj
    # 
    # ttt = list_tab_dict("worksp","is_active")
    # {'0': 'archive', '1': 'ready', '3': 'draft'} 
    # 
    # see gen table
# example: is_active on table worksp , have a dictionary:
#| 91 | worksp_dict | 0    |         1 | 20....56 | {"is_active": {"0": "archive", "1": "ready", "3": "draft"}}      
# data stored in table "gen"
