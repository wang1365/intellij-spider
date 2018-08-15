from enum import Enum, unique

"""
模板中配置规则的选项名称
"""


@unique
class Keys(Enum):
    # 解析节点名称
    NAME = 'name'

    # 正则表达式
    REGEX = 'regex'

    # 匹配模式，'0'：第一个匹配（缺省） '1':所有匹配
    SEARCH_MODE = 'search_mode'

    # 匹配结果获取，支持如下方式：'$0', 'hello $1', 'http://www.test.com?p1=$1&p2=$2'
    QUERY = 'query'

    # 子解析项
    CHILDREN = 'children'

    # 被匹配内容来源, '0':网页内容(缺省) '1': 网页链接
    SOURCE = 'source'

    # 解析项类型，'0':普通(缺省) '1': 需要提取链接
    TYPE = 'type'

    LINK_RULE = 'link_rule'
    REMOVE_HTML = 'remove_html'
    JSONFIED = 'jsonfied'
    FUNCTION = 'function'
    UNICODE_TO_CN = 'unicode_to_cn'

    POST_REPLACES = 'post_replaces'

    # 翻页使用的5个变量名称
    VAR_CURRENT_PAGE = 'currentPage'
    VAR_PAGE_COUNT = 'pageCount'
    VAR_PAGE_ITEM_TOTAL_COUNT = 'totalCount'
    VAR_PAGE_STEP = 'pageStep'
    # 有些网站对最大翻页数有限制，使用该变量进行限定
    VAR_PAGE_MAX_COUNT = 'maxPageCount'
    VAR_PAGE_URL_PATTERN = 'pageUrlPattern'


@unique
class NodeType(Enum):
    NORMAL = 0
    LINK = 1
    VARIOUS = 2
    PAGE_FLIP = 3
