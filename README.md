# intellij-spider
一个通用的爬虫应用

## 使用说明
抓取一个网站内容时不需要写代码，只需要配置模板即可，下面以抓取 [*寿光蔬菜网-蔬菜资讯*](http://sg.vegnet.com.cn/News/List) 中的所有文章（包括翻页的）为例
说明如何抓取

### 创建抓取应用程序
每一个新的应用放在`apps/`下面, 例如 [*寿光蔬菜网*](./apps/sgsc/app.py) `apps/sgsc/app.py`

### 给应用配置解析模板
解析模板用于解析HTTP请求返回的内容HTML/JSON等，目前仅支持正则表达式解析，每一类链接应该配置一个对应的解析模板，
以`寿光蔬菜网`应用为例，在`template/`下面配置了2个模板：
* sgsc_page  
`template/sgsc_page.py` 用于解析 [*文章列表页*](http://sg.vegnet.com.cn/News/List) , 列表页首页和其他分页都是用这个模板解析，
解析结果中包含所有文章正文对应的链接
* sgsc_article  
`template/sgsc_article.py` 用于解析 [*文章正文*](http://sg.vegnet.com.cn/News/Detail/1220502) , 列表页首页和其他分页都是用这个模板解析，
解析结果中包含文章标题、来源、日期、正文内容等等。

配置解析模板支持模板测试功能，测试使用`template/util.py`的`test`函数即可，具体可参考示例模板。

### 如何启动抓取应用
* 切换当前目录到`intellij-spider/intellij-spider/`
* 立即抓取使用：
`python -m apps.sgsc.app`
* 每天凌晨2点定时抓取使用：
`python -m apps.sgsc.app true 02:00 `