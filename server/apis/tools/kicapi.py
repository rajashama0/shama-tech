    
#
# return ok message from python server side
#
def api_ok(more={}):
    print(f',"allow":1')
    print(mores(more))

#
# return Error message from python server side
#
def api_err(msg,more={}):
    print(f',"allow":0,"msg":"{msg}"')
    print(mores(more))
    return 0


#
# structured api success for external calls
#
def api_success(data=None):
    import json
    if data is None:
        data = {}
    print(',"allow":1,"success":true')
    print(f',"data":{json.dumps(data, ensure_ascii=False)}')
    return 1


#
# structured api error for external calls
#
def api_fail(code, msg, more=None):
    import json
    if more is None:
        more = {}
    err = {"code": code, "message": msg}
    if type(more) is dict:
        for k in more:
            err[k] = more[k]
    print(',"allow":0,"success":false')
    print(f',"error":{json.dumps(err, ensure_ascii=False)}')
    return 0
    

#
# return more keys in an object string - as result coming back from python server side
# object -> to string
# { "price":100.40 , "mam" : 0.18 } ->   ,"price":"100.40","mam":"0.18" 
#
# so the answer from api will return more data from the server , for use or for logs
#
def mores(more):
    s = ""
    for o in more:
        s += f',"{o}":"{more[o]}"'
    return s
