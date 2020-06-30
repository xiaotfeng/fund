import requests
import json
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd
import datetime
import sys
import color

# 抓取单只基金
def Fund(code):  
    url = 'https://api.doctorxiong.club/v1/fund/detail'
    params = {
        'code':code
    }
    response = requests.get(url, params = params)
    res = response.text
    result = json.loads(res)
    return result
 
# 抓取网页
def get_url(url, params=None, proxies=None):
    rsp = requests.get(url, params=params, proxies=proxies)
    rsp.raise_for_status()
    return rsp.text

# 从网页抓取数据
def get_fund_data(code,per=10,sdate='',edate='',proxies=None):
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
    params = {'type': 'lsjz', 'code': code, 'page':1,'per': per, 'sdate': sdate, 'edate': edate}
    html = get_url(url, params, proxies)
    soup = BeautifulSoup(html, 'html.parser')

    # 获取总页数
    pattern=re.compile(r'pages:(.*),')
    result=re.search(pattern,html).group(1)
    pages=int(result)

    # 获取表头
    heads = []
    for head in soup.findAll("th"):
        heads.append(head.contents[0])

    # 数据存取列表
    records = []

    # 从第1页开始抓取所有页面数据
    page=1
    while page<=pages:
        params = {'type': 'lsjz', 'code': code, 'page':page,'per': per, 'sdate': sdate, 'edate': edate}
        html = get_url(url, params, proxies)
        soup = BeautifulSoup(html, 'html.parser')

        # 获取数据
        for row in soup.findAll("tbody")[0].findAll("tr"):
            row_records = []
            for record in row.findAll('td'):
                val = record.contents

                # 处理空值
                if val == []:
                    row_records.append(np.nan)
                else:
                    row_records.append(val[0])

            # 记录数据
            records.append(row_records)

        # 下一页
        page=page+1

    # 数据整理到dataframe
    np_records = np.array(records)
    data= pd.DataFrame()
    for col,col_name in enumerate(heads):
        data[col_name] = np_records[:,col]
    return data
    
# 指定基金的涨跌幅
def GrowthExtent(code,sdate='',edate=''):
    data=get_fund_data(code,per=49,sdate=sdate,edate=edate)
    # 修改数据类型
    data['净值日期']=pd.to_datetime(data['净值日期'],format='%Y/%m/%d')
    data['单位净值']= data['单位净值'].astype(float)
    data['累计净值']=data['累计净值'].astype(float)
    data['日增长率']=data['日增长率'].str.strip('%').astype(float)
    #连续涨跌幅
    growth_rate_list = data['日增长率']
    continuous_growth = growth_rate_list[0]
    if growth_rate_list[0] > 0:
        n = 1
        while growth_rate_list[n] > 0:
            continuous_growth += growth_rate_list[n]
            n += 1
    if growth_rate_list[0] < 0:
        n = 1
        while growth_rate_list[n] < 0:
            continuous_growth += growth_rate_list[n]
            n += 1
    
    # 按照日期升序排序并重建索引
    data=data.sort_values(by='净值日期',axis=0,ascending=True).reset_index(drop=True)
    data = data.dropna(axis=0)
    growth = []
    for i in range(len(data)):
        growth.append(data['日增长率'].iloc[i])
    growth_up = [i for i in growth if i > 0]
    growth_down = [i for i in growth if i < 0]
    result = {}
    result['max'] = str(max(growth))+'%'
    result['min'] = str(min(growth))+'%'
    result['avarage'] = '{:.2f}%'.format(np.mean(growth))
    result['avarage_up'] = '{:.2f}%'.format(np.mean(growth_up))
    result['avarage_down'] = '{:.2f}%'.format(np.mean(growth_down))
    result['continuous_growth'] = {}
    result['continuous_growth']['extent'] = continuous_growth
    result['continuous_growth']['day'] = n
        
    return result

def ShowDeatil(code_list,sdate='',edate='',key=''):
    if len(key) == 6:
        code_list = [key]
    for code in code_list:
        detail = Fund(code)
        data = detail['data']
        ComputeGrowthValue = GrowthExtent(code)
        print('{} ({})'.format(data['name'],data['code']))
        print_out = '★ 当前涨幅: '+data['expectGrowth']+'% ★'
        continuous_growth = ComputeGrowthValue['continuous_growth']
        print_extent = '最近{}天连续累计涨幅: {}%'.format(continuous_growth['day'],continuous_growth['extent'])
        
        if not key:
            if float(data['expectGrowth']) > 0:
                color.printRed(print_out)
            else:
                color.printGreen(print_out)
            if continuous_growth['day'] > 1:
                if continuous_growth['extent'] > 0:
                    color.printRed(print_extent)
                else:
                    color.printGreen(print_extent)
            print(data['expectWorthDate'])
        else:
            print(print_out)
        print('-----------------------------')
        
        if key == 'd' or len(key) == 6:
            print('历史最大涨幅:{}\n历史平均涨幅:{}\n历史最大跌幅:{}\n历史平均跌幅:{}\n历史平均:{}\n{}'.format(
                ComputeGrowthValue['max'],
                ComputeGrowthValue['avarage_up'],            
                ComputeGrowthValue['min'],
                ComputeGrowthValue['avarage_down'],         
                ComputeGrowthValue['avarage'],
                print_extent if continuous_growth['day'] > 1 else 'None'
            ))
            
            key_list = []
            k_list = list(ComputeGrowthValue.values())
            del k_list[-1]
            for k in k_list:
                key_list.append(float(k.strip('%')))
            key_list.append(float(data['expectGrowth']))
            key_list = sorted(key_list)
            #print(key_list)
            result = ''
            for i in key_list:
                if i == float(data['expectGrowth']):
                    i = '({})'.format(i)
                result += '_{}%_'.format(i)
            print('横向比较:' +result+'\n')

        
if __name__ == '__main__':
    try:
        key = sys.argv[1]
    except IndexError:
        key = ''
    time_obj = datetime.datetime.now()
    edate = "{}-{}-{}".format(time_obj.year,time_obj.month,time_obj.day) #当前日期
    code_list1 = [
    '000834',
    '006308',
    '006228',
    '001218',
    '110020',
    '000008',
    '320007'
    ]
    code_list2 = [
    '005520',
    '003095',
    '006274',
    '160222',
    '110020',
    '161130',
    '000220',
    '001171',
    ]
    code_list = code_list1
    ShowDeatil(code_list,sdate='2020-01-01',edate=edate,key=key)