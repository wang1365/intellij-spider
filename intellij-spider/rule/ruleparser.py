import re
import json
import datetime
from rule.rule import RuleNode, Rule
from common import keys


class RuleParserResult(object):
    def __init__(self, data=None, linked_urls=None):
        self._data = data if data else {}
        self._linked_urls = linked_urls if linked_urls else {}

    @property
    def data(self) -> {}:
        return self._data

    @property
    def linked_urls(self) -> {}:
        return self._linked_urls


class RuleParser(object):
    """
    内容解析器，对上下文应用指定的规则进行解析，
    """

    def __init__(self, rule: Rule, content: str, url: str):
        self._rule = rule
        self._content = content
        self._url = url
        self._vars = {}

    def get_var(self, k):
        return self._vars.get(k)

    def set_var(self, k, v):
        print('set new var:', k, v)
        if self._vars.get(k):
            print('Warning, overwrite existed key:', k, self._vars.get(k), v)
        self._vars[k] = v

    def parse(self) -> RuleParserResult:
        ret, link_items = {}, {}
        for node in self._rule.nodes:
            k, v, items = self.parse_node(node, self._content)
            if k and v:
                ret[k] = v
            link_items = {**link_items, **items}

        wrapped_result = {
            '_collectTime': datetime.datetime.now().isoformat(),
            '_url': self._url,
            '_rule': self._rule.name,
            '_source': ret
        }
        return RuleParserResult(wrapped_result, link_items)

    def parse_node(self, rule_node: RuleNode, content: str):
        if not rule_node:
            raise ValueError

        if not content:
            return rule_node.name, None, {}

        # 其他翻页提取
        if rule_node.type == RuleNode.TYPE_PAGE_FLIP:
            value, new_links = self.parse_node_page_flip(rule_node)
            return rule_node.name, value, new_links

        content = content if rule_node.source == rule_node.SOURCE_CONTENT else self._url
        if rule_node.search_mode == RuleNode.REGEX_FIND_1ST:
            value, new_links = self.parse_node_search_1st(rule_node, content)
        else:
            value, new_links = self.parse_node_search_all(rule_node, content)
        return rule_node.name, value, new_links

    def parse_node_page_flip(self, rule_node: RuleNode):
        """
        对于存在翻页的页面，该函数用于提起其他的页面链接，仅对第一页生效
        :param rule_node:
        :return:
        """
        value, new_links = [], {}
        current_page = self.get_current_page()
        page_count = self.get_page_count()
        page_step = self.get_page_step()
        page_url_pattern = self.get_page_url_pattern()

        # 只有当前页面是第一页时才提取其他页面
        if current_page == 1 and page_step > 0 and page_count > 0 and page_url_pattern:
            start = 2 if page_step == 1 else 1
            end = page_count + 1 if page_step == 1 else page_count
            for i in range(start, end):
                page = page_url_pattern.format(page=i*page_step)
                value.append(page)
                new_links[page] = rule_node.link_rule
        return value, new_links

    def get_current_page(self):
        current_page = 0
        try:
            data = self.get_var(keys.VAR_CURRENT_PAGE)
            if data:
                current_page = int(data)
        except Exception as e:
            print('get_current_page failed!', e)
        return current_page

    def get_page_count(self):
        page_count = 0
        try:
            data = self.get_var(keys.VAR_PAGE_COUNT)
            if data:
                page_count = int(data)
        except Exception as e:
            print('get_page_count failed!', e)
        return page_count

    def get_page_step(self):
        page_step = 1
        try:
            data = self.get_var(keys.VAR_PAGE_STEP)
            if data:
                page_step = int(data)
        except Exception as e:
            print('get_page_step failed!', e)
        return page_step

    def get_page_url_pattern(self):
        return self.get_var(keys.VAR_PAGE_URL_PATTERN)

    def parse_node_search_1st(self, node: RuleNode, content):
        key, value, new_links = node.name, {}, {}
        m = None
        for item in node.regex_items:
            # 查找第一个匹配
            search_ret = re.search(item.regex, content)
            if not search_ret:
                print('Regex match failed, re: {}, {}'.format(item.regex, self._url))
                continue

            g0, groups = search_ret.group(0), search_ret.groups()
            # $0,$1...取值
            m = self.query_content(item.query, g0, groups)
            if m:
                break
        if not m:
            return None, {}

        # 后处理，去除HTML标签等
        m = self.post_process(node, m)
        if not node.children:
            # 没有子解析项，直接输出匹配后的内容
            if node.jsonfied:
                try:
                    m = json.loads(m, encoding='utf8')
                except Exception as e:
                    print('Convert to json failed !', m, e)
                    m = None
            value = m
            if node.type == RuleNode.TYPE_VAR:
                self.set_var(node.name, m)
            # 当前解析节点需要提取链接
            if node.type == node.TYPE_LINK:
                if isinstance(m, str):
                    new_links[m] = node.link_rule
                elif isinstance(m, list):
                    for mi in m:
                        new_links[mi] = node.link_rule
        else:
            # 有子解析项
            value, new_links = self.parse_child_nodes(node.children, m)
        return value, new_links

    def parse_node_search_all(self, rule_node, content):
        key, value, new_links = rule_node.name, [], {}

        m = []
        for item in rule_node.regex_items:
            # 查找第一个匹配, 用于保存$0
            search_ret = re.search(item.regex, content)
            if not search_ret:
                print('Regex match failed, re: {}, {}'.format(item.regex, self._url))
                continue
            # 需要查找所有匹配的场景，返回数组
            result = re.findall(item.regex, content)

            if not result:
                print('{} parse failed'.format(rule_node.name))
            else:
                # $0,$1...取值
                result = [self.query_content_for_multi(item.query, groups, groups) for groups in result]
                m.extend(result)

        # 后处理，去除HTML标签等
        m = [self.post_process(rule_node, content=i) for i in m]

        if not rule_node.children:
            # 没有子解析项，直接输出匹配后的内容
            value = m if not rule_node.jsonfied else [json.loads(i, encoding='utf8') for i in m]
            # 当前解析节点需要提取链接
            if rule_node.type == rule_node.TYPE_LINK:
                for m_item in m:
                    new_links[m_item] = rule_node.link_rule
        else:
            # 有子解析项，遍历所有匹配的结果，每个结果应用子解析规则，然后合并结果
            for m_item in m:
                child_rt, child_links = self.parse_child_nodes(rule_node.children, m_item)
                value.append(child_rt)
                new_links = {**new_links, **child_links}
        return value, new_links

    def parse_child_nodes(self, children, content):
        ret, linked_urls = {}, {}
        for rule in children:
            k, v, items = self.parse_node(rule, content)
            if k and v:
                # 合并各个子节点解析的结果
                ret[k] = v
            # 合并各个子节点解析提取的链接
            linked_urls = {**linked_urls, **items}
        return ret, linked_urls

    def post_process(self, rule: RuleNode, content: str):
        ret = content
        if rule.remove_html:
            ret = re.sub('<[^>]+?>', '', ret)
            ret = ret.strip()
        ret = ret.replace('&nbsp;', '').replace('\n\n', '')

        # Unicode转中文
        if rule.unicode_to_cn:
            ret = ret.encode().decode('unicode_escape')

        # 字符串替换处理
        if rule.post_replaces:
            for pr in rule.post_replaces:
                if isinstance(pr, (list, tuple)) and len(pr) >= 2:
                    ret = re.sub(pr[0], pr[1], ret)

        # 变量替换
        ret = self.replace_vars(ret)

        # 执行自定义函数, 函数必须最后执行
        if rule.function:
            # result = rule.function(content, self._url)
            ret = rule.function(self)(ret)
        return ret

    def query_content(self, query, content, groups):
        if isinstance(content, str):
            query = query.replace('$0', content)

        if isinstance(groups, (list, tuple)):
            for i, g in enumerate(groups):
                if isinstance(groups[i], str):
                    query = query.replace('${}'.format(i + 1), groups[i])

        query = self.replace_vars(query)
        return query

    def query_content_for_multi(self, query, content, groups):
        if '$0' in query:
            return query.replace('$0', content)

        if isinstance(groups, str):
            query = query.replace('$1', groups)

        if isinstance(groups, (list, tuple)):
            for i, g in enumerate(groups):
                if isinstance(groups[i], str):
                    query = query.replace('${}'.format(i + 1), groups[i])
        query = self.replace_vars(query)
        return query

    def replace_vars(self, content: str):
        """
        变量替换，变量格式为${various}, 替换内容为名称为various的解析项，且
        该解析项类型为key.TYPE == RuleNode.TYPE_VAR
        :param content: 源内容
        :return:
        """
        ret = re.findall('\${(\S+?)}', content)
        if ret:
            for item in ret:
                var_name = item.strip()
                var_value = self.get_var(var_name)
                if var_name and var_value:
                    content = content.replace('${%s}' % var_name, var_value)
        return content


def test_replace_vars():
    cp = RuleParser(Rule('app'), "", "")
    cp.set_var('a', 'hello')
    cp.set_var('b', 'bbbbb')
    result = cp.replace_vars('${a}-${a}-${b}')
    assert result == 'hello-hello-bbbbb'


if __name__ == '__main__':
    test_replace_vars()
