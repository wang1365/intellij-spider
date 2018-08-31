from appcommand import start_app
from config import app_config, ProxyMapping, FailureCondition

"""
执行方式：
1. 切换到intellij-spider/intellij-spider/目录
2. 立即执行一次： python -m apps.sgsc.app true
3. 每天定时执行： python -m apps.sgsc.app
"""

app_config.proxy_mapping = ProxyMapping().add_url_proxy('sg.vegnet.com.cn', {'http':'http://proxy.com:8080'})
app_config.fail_conditions = FailureCondition({'vegnet.com.cn': ['下载失败', '"error_code":-1']})

start_app(appname='shouguangshucai', urls=['http://sg.vegnet.com.cn/News/List'], rule_name='sgsc_page')
