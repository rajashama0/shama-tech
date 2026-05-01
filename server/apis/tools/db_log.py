#
# centralized log helper
# 
# add before :   log_id = add_log("receipt-agoda sinit" ,deb_data)
# add after  :   add_log_res(log_id,json.dumps(resb))

# ver : 1.02 - zne

from tools.sql import *
import json

#                     vvvvvvvvv                                             v 
#                     send_text can be object - You don't need to convert to string f-string will do it)
#                     vvvvvvvvv                                             v 
def add_log(act_type ,send_text, data=""): #                                v
    w=insert_to_sql({'table':'logs','set':{"act_type":act_type, "send_text":f'{send_text}'}})
    id = w['id']
    if type(data) is dict:
        add_to_data("logs",id,data)
    return id


def add_log_res(log_id,response):
    insert_to_sql({'table':'logs',
                   'id':log_id,
                   'set':{"response":f'{response}'}
                  })
    return 1
