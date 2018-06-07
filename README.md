# intellij-spider
一个通用的爬虫应用, 只需要配置解析模板，对框架和代码没有侵入性，无需编写代码。

## 环境
* Python 3.4+
* 依赖库参考 [requirements](./requirements.txt) .
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
`python -m apps.sgsc.app true`
* 每天凌晨2点定时抓取使用：
`python -m apps.sgsc.app false 02:00 `

### 抓取结果
* 抓取结果存储在文件中，按照模板每天存储一个文件，存储位置参考`config.py`的`OUTPUT_DIR`

### 反扒
* 缓存避免重抓，抓取时使用缓存存储每个抓取的链接结果，多次抓取同一个链接不会重复网络请求，缓存有效期为1个自然日
* 支持代理设置，参考`config.py`的`ProxyMapping`, 可以对不同的URL(正则匹配)配置不同的代理
* 支持gevent异步抓取，同步抓取使用多线程，工作线程数可配置