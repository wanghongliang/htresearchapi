# from pytdx.hq import TdxHq_API
# api = TdxHq_API()
# if api.connect('116.205.163.254',7709): # 连接到指定服务器
#    print("连接成功")
# else:
#    print("连接失败")
from pytdx.exhq import *
from pytdx.hq import *

from pytdx.hq import  TdxHq_API
api=TdxHq_API()

with api.connect('116.205.163.254',7709):
    qt = api.get_security_quotes([(0, '000001'), (1, '600300')])
    for _ord in qt:
        print( _ord )

    #查询分时行情
    md = api.get_minute_time_data(1, '600300')
    print(md)

    td = api.get_transaction_data(TDXParams.MARKET_SZ, '000001', 0, 30)
    print(td)
    #print(qt)
#       data=[]
#       for i in range(10):
#          data+=api.get_security_bars(9,0,'000001',(9-i)*800,800)
#
#
#
# print(api.to_df(data))

api.disconnect()