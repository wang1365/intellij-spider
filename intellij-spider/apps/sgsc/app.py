from appcommand import start_app

"""
执行方式：
1. 切换到intellij-spider/intellij-spider/目录
2. 立即执行一次： python -m apps.sgsc.app true
3. 每天定时执行： python -m apps.sgsc.app
"""


start_app(appname='shouguangshucai', url='http://sg.vegnet.com.cn/News/List', rule_name='sgsc_page')
