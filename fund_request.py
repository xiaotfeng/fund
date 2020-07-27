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
import argparse
import time

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
    
#抓取大盘
def stock_board():  
    url = 'https://api.doctorxiong.club/v1/stock/board'
    response = requests.get(url)
    res = response.text
    stock_board = json.loads(res)
    if stock_board['code'] == 200:
        Astock = stock_board['data'][0]
        name = Astock['name']
        close = Astock['close']
        price = Astock['price']
        changePercent = Astock['changePercent']
        date = Astock['date']
        points = float(price)-float(close)
        print('{}：{} 涨幅点数：{:.2f} 百分比：{}%\n'.format(
            name,
            price,
            points,
            changePercent
        ))
    else:
        print('大盘请求接口异常')
    # for stock in stock_board['data']:
        # name = stock['name']
        # close = stock['close']
        # price = stock['price']
        # changePercent = stock['changePercent']
        # date = stock['date']
        # points = float(price)-float(close)
        # print('{}：{} 涨幅点数；{:.2f} 百分比：{}%'.format(
            # name,
            # price,
            # points,
            # changePercent
        # ))
 
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
def GrowthExtent(code,sdate,edate):
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
    elif growth_rate_list[0] < 0:
        n = 1
        while growth_rate_list[n] < 0:
            continuous_growth += growth_rate_list[n]
            n += 1
    else:
        n = 1
    
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

def ShowDeatil(code_list,sdate,edate,key,sigle_code_num=''):
    if sigle_code_num:
        code_list = [sigle_code_num]
    for code in code_list:
        detail = Fund(code)
        if detail['code'] != 200:
            assert('json return code error!')
        data = detail['data']
        ComputeGrowthValue = GrowthExtent(code,sdate,edate)
        print('{} ({})'.format(data['name'],data['code']))
        print_out = '★ 当前涨幅 ★:      '+data['expectGrowth']+'%'
        continuous_growth = ComputeGrowthValue['continuous_growth']
        print_extent = '最近{}天连续累计涨幅: {:.2f}%'.format(continuous_growth['day'],continuous_growth['extent'])
        
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
            print('-----------------------------')
        
        #if key == 'd' or len(key) == 6:
            # print('历史最大涨幅:{}\n历史平均涨幅:{}\n历史最大跌幅:{}\n历史平均跌幅:{}\n历史平均:{}\n{}'.format(
                # ComputeGrowthValue['max'],
                # ComputeGrowthValue['avarage_up'],            
                # ComputeGrowthValue['min'],
                # ComputeGrowthValue['avarage_down'],         
                # ComputeGrowthValue['avarage'],
                # print_extent if continuous_growth['day'] > 1 else ' '
            # ))
        else:
            print(print_out)
            print(print_extent) if continuous_growth['day'] > 1 else ' '
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
            print('{}天内的横向比较:   {}'.format(args.time, result))
            
            WeekdayAvg = WeekdayAvgGrowth(code,args.time)
            print('{}天内每天平均涨幅：一：{} 二：{} 三：{} 四：{} 五：{}'.format(args.time, WeekdayAvg['mon'],WeekdayAvg['tues'],WeekdayAvg['wed'],WeekdayAvg['thur'],WeekdayAvg['fri']))
            
            extent = float(format(continuous_growth['extent'],'.2f'))
            avg_up = float(ComputeGrowthValue['avarage_up'].strip('%'))
            avg_down = float(ComputeGrowthValue['avarage_down'].strip('%'))
            avg = avg_up if extent > 0 else avg_down
            print_extent = '连续涨跌幅已经接近{}天内的平均值'.format(args.time)
            if abs(extent-avg) <= 0.5:
                if extent > 0:
                    color.printRed(print_extent)
                else:
                    color.printGreen(print_extent)
            print('\n')

def BeforeDay(days):
    # 返回距离今天day天前的日期
    days = int(days)
    beforday = (datetime.datetime.now()-datetime.timedelta(days = days))
    formatday = "{}-{}-{}".format(beforday.year,beforday.month,beforday.day)
    return formatday

def WeekdayAvgGrowth(code,day):  # json为fund的json返回值
    detail = Fund(code)
    day = int(day)
    if detail['code'] != 200:
        assert('json return code error!')
    netWorthData_list = detail['data']['netWorthData']
    netWorthData_list_day = netWorthData_list[-day:]
    weeklist = {'mon':[],'tues':[],'wed':[],'thur':[],'fri':[]}
    for i in netWorthData_list_day:
        weekday = datetime.datetime.strptime(i[0], '%Y-%m-%d').weekday() # 判断该日期周几
        weekday = weekday+1
        #print(str(weekday)+'    '+i[0]+'   '+str(i[2]))
        if weekday == 1:
            weeklist['mon'].append(i[2])
        elif weekday == 2:
            weeklist['tues'].append(i[2])
        elif weekday == 3:
            weeklist['wed'].append(i[2])
        elif weekday == 4:
            weeklist['thur'].append(i[2])
        elif weekday == 5:
            weeklist['fri'].append(i[2])
    weeklist_avg = {k: format(float(sum(v))/len(v), '.2f') for k,v in weeklist.items()}
    return weeklist_avg
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='***参数列表***')
    parser.add_argument('-d', '--detail', action='store_true', default=False, dest='key', help='显示基金的涨幅详情')
    parser.add_argument('-l', '--list', default='1', help='选择基金列表')
    parser.add_argument('-t', '--time', default='100', help='统计历史天数内的基金涨幅')
    parser.add_argument('-s', '--sigle_code_num', help='单独的基金代码')
    args = parser.parse_args()
    
    time_obj = datetime.datetime.now()
    edate = "{}-{}-{}".format(time_obj.year,time_obj.month,time_obj.day) #当前日期
    stock_board()
    sigle_code_num = args.sigle_code_num
    sdate = BeforeDay(args.time)
    key = args.key
    code_list1 = [
    '000834',
    '000008',
    '006308',
    '003096',
    '519005',
    '519674',
    '001630',
    '161725',
    '001071',
    '320007',
    '001616',
    '002939',
    ]
    code_list2 = [
    '000834',
    '006274',
    '008086',
    '519193',
    '320007',
    '002939',
    ]
    code_list3 = [
    '161005',
    '000083',
    ]
    if args.list == '1':
        code_list = code_list1
    elif args.list == '2':
        code_list = code_list2
    elif args.list == '3':
        code_list = code_list3
    else:
        assert('list code error')
    
    
    try:    
        ShowDeatil(code_list,sdate,edate,key,sigle_code_num)
    except KeyboardInterrupt:
        color.printYellow('\n已手动停止')