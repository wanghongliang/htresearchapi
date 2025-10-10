from datafrom.pytdx_stock_analyzer import PytdxStockAnalyzer

from pytdx.exhq import *
from pytdx.hq import *

from pytdx.hq import TdxHq_API

# 示例用法
if __name__ == "__main__":

    # # 创建分析器并执行分析
    # analyzer = PytdxStockAnalyzer()
    # result = analyzer.full_analysis( sample_data )
    #
    # # 打印分析报告
    # analyzer.print_analysis_report()



    api = TdxHq_API()

    data = []
    with api.connect('116.205.163.254', 7709):

        #003816
        #MARKET_SH  MARKET_SZ
        #td = api.get_transaction_data(TDXParams.MARKET_SH, '513630', 0, 30)
        data = api.get_transaction_data(TDXParams.MARKET_SH, '513630', 0, 30)
        #for ord in data:
            #print( ord )
            #data.append( ord )
        #print(td)

    # 创建分析器并执行分析
    analyzer = PytdxStockAnalyzer()
    result = analyzer.full_analysis( data )

    # 打印分析报告
    analyzer.print_analysis_report()

    api.disconnect()
