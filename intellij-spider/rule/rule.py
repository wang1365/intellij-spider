import traceback

from common import util
from common.consts import Keys, NodeType
from common.log import logger
from collections import defaultdict
from enum import Enum


class RegexItem(object):
    def __init__(self, regex: str, query: str):
        self._regex, self._query = regex, query

    @property
    def regex(self):
        return self._regex

    @property
    def query(self):
        return self._query


class RuleNode(object):
    """
    解析节点，树状结构，可以包含若干个子解析节点
    """
    REGEX_FIND_1ST = 0
    REGEX_FIND_ALL = 1

    SOURCE_CONTENT = 0
    SOURCE_URL = 1

    def __init__(self, name):
        self._name = name
        # 解析节点类型，常规/链接提取/变量/翻页提取
        self._type = NodeType.NORMAL
        # 正则表达式
        self._regex_items = []
        # 匹配结果取值
        self._query = '$0'
        # 正则匹配模式，匹配第一个/匹配所有
        self._search_mode = self.REGEX_FIND_1ST
        # 提取的链接后续应用的解析规则Rule
        self._link_rule = None
        # 内容来源，HTTP返回body，或者当前URL链接
        self._source = self.SOURCE_CONTENT
        # 子解析项列表
        self._children = []
        # 是否去除内容中的HTML标签
        self._remove_html = False
        # 是否将内容直接转为JSON
        self._jsonfied = False
        # 将内容应用于function
        self._function = None
        # unicode字符转为utf8
        self._unicode_to_cn = False
        self._post_replaces = []

    @property
    def name(self):
        return self._name

    @property
    def children(self):
        return self._children

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, v):
        self._type = v

    @property
    def regex_items(self):
        return self._regex_items

    @regex_items.setter
    def regex_items(self, v):
        self._regex_items = v

    @property
    def search_mode(self):
        return self._search_mode

    @search_mode.setter
    def search_mode(self, v):
        self._search_mode = v

    @property
    def link_rule(self):
        return self._link_rule

    @link_rule.setter
    def link_rule(self, v):
        self._link_rule = v

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, v):
        self._query = v

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, v):
        self._source = v

    @property
    def remove_html(self):
        return self._remove_html

    @remove_html.setter
    def remove_html(self, v):
        self._remove_html = v

    @property
    def jsonfied(self):
        return self._jsonfied

    @jsonfied.setter
    def jsonfied(self, v):
        self._jsonfied = v

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, v):
        self._function = v

    @property
    def unicode_to_cn(self):
        return self._unicode_to_cn

    @unicode_to_cn.setter
    def unicode_to_cn(self, v):
        self._unicode_to_cn = v

    @property
    def post_replaces(self):
        return self._post_replaces

    @post_replaces.setter
    def post_replaces(self, v):
        self._post_replaces = v

    def add_child(self, node):
        self._children.append(node)
        return self

    @classmethod
    def from_json(cls, data: dict):
        """
        从JSON中生成解析规则
        :param data: json数据
        :return: 解析规则Rule
        """
        node = None
        try:

            raw_name = data[Keys.NAME]
            node = RuleNode(raw_name.value if isinstance(raw_name, Enum) else str(raw_name))

            regex_items = data.get(Keys.REGEX)
            if regex_items and isinstance(regex_items, (tuple, list)):
                for item in regex_items:
                    node.regex_items.append(RegexItem(item[0], item[1]))
            else:
                logger.info('Init rule warning, invalid regex for item: {}'.format(data[Keys.NAME]))

            query = data.get(Keys.QUERY)
            if query:
                node.query = query

            node.type = data.get(Keys.TYPE) or NodeType.NORMAL

            node.remove_html = cls.get_option(data.get(Keys.REMOVE_HTML), False, {'0': False, '1': True})
            node.jsonfied = cls.get_option(data.get(Keys.JSONFIED), False, {'0': False, '1': True})

            link_rule = data.get(Keys.LINK_RULE)
            if link_rule:
                node.link_rule = link_rule

            func = data.get(Keys.FUNCTION)
            if func:
                node.function = func

            max_page_count = data.get(Keys.VAR_PAGE_MAX_COUNT)
            if max_page_count:
                node.max_page_count = int(max_page_count)

            unicode_to_cn = data.get(Keys.UNICODE_TO_CN)
            if unicode_to_cn:
                node.unicode_to_cn = (unicode_to_cn == '1')

            post_replaces = data.get(Keys.POST_REPLACES)
            if isinstance(post_replaces, (list, tuple, set)):
                node.post_replaces = post_replaces

            node.search_mode = RuleNode.REGEX_FIND_ALL if data.get(Keys.SEARCH_MODE) == '1' else RuleNode.REGEX_FIND_1ST
            node.source = RuleNode.SOURCE_URL if data.get(Keys.SOURCE) == '1' else RuleNode.SOURCE_CONTENT

            items = data.get(Keys.CHILDREN)
            if items:
                for item in items:
                    node.children.append(cls.from_json(item))
        except Exception as e:
            logger.info('Generate rule error from json, {} {}'.format(e, data))
            traceback.logger.info_exc()
        return node

    @classmethod
    def get_option(cls, key, default, options: dict):
        return defaultdict(lambda: default, options)[key]


class Rule(object):
    """
    HTML解析规则，解析一个HTML时需要指定一个Rule
    该规则下面包含若干个解析节点
    """

    def __init__(self, name):
        self._nodes = []
        self._name = name

    def add_node(self, node: RuleNode):
        self._nodes.append(node)

    @property
    def nodes(self):
        return self._nodes

    @property
    def name(self):
        return self._name

    @classmethod
    def from_json(cls, rule_name, data: list):
        if not isinstance(data, list):
            logger.info('Error, cannot convert to rule from a non-json data')
            return None
        rule = Rule(rule_name)
        for item in data:
            rule.add_node(RuleNode.from_json(item))
        return rule

    @classmethod
    def find_by_name(cls, rule_name):
        return cls.from_json(rule_name, util.get_rule(rule_name))


class RuleNodeFunction(object):
    def __init__(self, rule):
        self._rule = rule

    def __call__(self, content, **kwargs):
        return self.execute(content, **kwargs)

    def execute(self, content, **kwargs):
        raise NotImplementedError


def test_rule_node():
    node = RuleNode.from_json({
        'name': 'wangxiaochuan'
    })

    assert node.name == 'wangxiaochuan'
    assert node is not None
    assert node.regex == '[\s\S]*'
    assert node.type == RuleNode.TYPE_COMMON
    assert node.query == '$0'
    assert not node.unicode_to_cn
    assert not node.function
    assert not node.jsonfied
    assert not node.post_replaces
    assert node.source == RuleNode.SOURCE_CONTENT
    assert not node.remove_html
    assert not node.link_rule

    data = {
        Keys.NAME: 'wangxiaochuan',
        Keys.REGEX: 'regix expression',
        Keys.QUERY: '$1-$2',
        Keys.JSONFIED: '1',
        Keys.TYPE: '2',
        Keys.LINK_RULE: 'link rule',
        Keys.FUNCTION: lambda x: 1,
        Keys.UNICODE_TO_CN: '1',
        Keys.SEARCH_MODE: '1',
        Keys.SOURCE: '1',
        Keys.REMOVE_HTML: '1'
    }
    node = RuleNode.from_json(data)

    assert node is not None
    assert node.regex == data[Keys.REGEX]
    assert node.type == RuleNode.TYPE_VAR
    assert node.query == data[Keys.QUERY]
    assert node.unicode_to_cn
    assert node.function == data[Keys.FUNCTION]
    assert node.jsonfied
    assert node.source == RuleNode.SOURCE_URL
    assert node.remove_html
    assert node.link_rule == data[Keys.LINK_RULE]


if __name__ == '__main__':
    test_rule_node()
