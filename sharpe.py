#先引入后面可能用到的包（package）
import pandas as pd  
import numpy as np
import matplotlib.pyplot as plt


#正常显示画图时出现的中文和负号
from pylab import mpl
mpl.rcParams['font.sans-serif']=['SimHei']
mpl.rcParams['axes.unicode_minus']=False

### 获取数据：tushare开源库（确认已安装好：pip install tushare）
import tushare as ts
#起始和结束日期可以自行输入，否则使用默认
def get_data(code,start_date="2009-01-01", end_date="2019-01-18"):
    df = ts.get_k_data(code, start=start_date, end=end_date)
    df.index=pd.to_datetime(df.date)
    return df.close
#返回收盘价

#以上证综指、贵州茅台、工商银行、中国平安为例
stocks={'sh':'上证综指','600519':'贵州茅台',
        '601398':'工商银行','601318':'中国平安'}
#获取上述股票（指数）的每日前复权收盘价
df=pd.DataFrame()
for code,name in stocks.items():
    df[name]=get_data(code)
    
df.head()

#以第一交易日2009年1月5日收盘价为基点，计算净值
df_new=df/df.iloc[0]
#将上述股票在回测期间内的净值可视化
df_new.plot(figsize=(16,7))
#图标题
plt.title('股价净值走势',fontsize=15)
#设置x轴坐标
my_ticks = pd.date_range('2008-01-01','2019-01-18',freq='Y')
plt.xticks(my_ticks,fontsize=12)
#去掉上、右图的线
ax=plt.gca()
ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
plt.show()

### 区间累计收益率(绝对收益率)
total_ret=df_new.iloc[-1]-1
TR=pd.DataFrame(total_ret.values,columns=['累计收益率'],index=total_ret.index)
TR

###年化收益率,假设一年以250交易日计算
annual_ret=pow(1+total_ret,250/len(df_new))-1
AR=pd.DataFrame(annual_ret.values,columns=['年化收益率'],index=annual_ret.index)
AR

#numpy:np.maximum.accumulate计算序列累计最大值
code='上证综指'
n_d=((np.maximum.accumulate(df[code])-df[code])/np.maximum.accumulate(df[code])).max()
#pandas使用cummax（）计算序列累计最大值
p_d=((df[code].cummax()-df[code])/df[code].cummax()).max()
#打印结果
print(f'numpy方法计算结果：{round(n_d*100,2)}%')
print(f'pandas方法计算结果：{round(p_d*100,2)}%')                    

#定义成函数，减少重复工作
def max_drawdown(df):
    md=((df.cummax()-df)/df.cummax()).max()
    return round(md,4)
md={}
for code,name in stocks.items():
    md[name]=max_drawdown(df[name])
#最大回撤率结果：
MD=pd.DataFrame(md,index=['最大回撤']).T
MD

#计算每日收益率
#收盘价缺失值（停牌），使用前值代替
rets=(df.fillna(method='pad')).apply(lambda x:x/x.shift(1)-1)[1:]
rets.head()

#市场指数为x，个股收益率为y
from scipy import stats
x=rets.iloc[:,0].values
y=rets.iloc[:,1:].values
AB=pd.DataFrame()
alpha=[]
beta=[]
for i in range(3):
#使用scipy库中的stats.linregress线性回归
#python回归有多种实现方式，
#如statsmodels.api的OLS，sklearn库等等
    b,a,r_value,p_value,std_err=stats.linregress(x,y[:,i])
    #alpha转化为年化
    alpha.append(round(a*250,3))
    beta.append(round(b,3))
AB['alpha']=alpha
AB['beta']=beta
AB.index=rets.columns[1:]
#输出结果：
AB

#使用公式法直接计算beta值（见前文公式）：
beta1=rets[['上证综指','贵州茅台']].cov().iat[0,1]/rets['上证综指'].var()
beta2=rets[['上证综指','工商银行']].cov().iat[0,1]/rets['上证综指'].var()
beta3=rets[['上证综指','中国平安']].cov().iat[0,1]/rets['上证综指'].var()
print(f'贵州茅台beta:{round(beta1,3)}')
print(f'工商银行beta:{round(beta2,3)}')
print(f'中国平安beta:{round(beta3,3)}')

#使用公式法直接计算beta值（见前文公式）：
#annual_ret是前文计算出来的年化收益率
alpha1=(annual_ret[1]-annual_ret[0]*beta1)
alpha2=(annual_ret[2]-annual_ret[0]*beta2)
alpha3=(annual_ret[3]-annual_ret[0]*beta3)
print(f'贵州茅台alpha:{round(alpha1,3)}')
print(f'工商银行alpha:{round(alpha2,3)}')
print(f'中国平安alpha:{round(alpha3,3)}')

#超额收益率以无风险收益率为基准
#假设无风险收益率为年化3%
exReturn=rets-0.03/250
#计算夏普比率
sharperatio=np.sqrt(len(exReturn))*exReturn.mean()/exReturn.std()
#夏普比率的输出结果
SHR=pd.DataFrame(sharperatio,columns=['夏普比率'])
SHR

###信息比率
#超额收益率以指数收益率或其他为基准
#这里以上证综指为基准
ex_return=pd.DataFrame() 
ex_return['贵州茅台']=rets.iloc[:,1]-rets.iloc[:,0]
ex_return['工商银行']=rets.iloc[:,2]-rets.iloc[:,0]
ex_return['中国平安']=rets.iloc[:,3]-rets.iloc[:,0]
ex_return.head()

#计算信息比率
information=np.sqrt(len(ex_return))*ex_return.mean()/ex_return.std()
#信息比率的输出结果
INR=pd.DataFrame(information,columns=['信息比率'])
INR

#将上述指标合并成一张表
indicators=pd.concat([TR,AR,MD,AB,SHR,INR],axis=1,join='outer',sort='False')
#结果保留三位小数
indicators.round(3)

