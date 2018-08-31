from common import keys, util

rule = [
    {
        keys.NAME: 'id',
        keys.REGEX: [('Detail/(\d+)', '$1')],
        keys.SOURCE: '1'
    },
    {
        keys.NAME: 'title',
        keys.REGEX: [('<h1>\s*(.*?)</h1>', '$1')],
    },
    {
        keys.NAME: 'source',
        keys.REGEX: [('【来源：(.*?)】', '$1')],
    },
    {
        keys.NAME: 'date',
        keys.REGEX: [('【时间：(.*?)】', '$1')],
    },
    {
        keys.NAME: 'content',
        keys.REGEX: [('<div id="fontzoom">([\s\S]*?)</div>', '$1')],
        keys.REMOVE_HTML: '1',
        keys.POST_REPLACES: [('&rdquo;', ''), ('&ldquo;', '')]
    },
]

if __name__ == '__main__':
    from pathlib import Path

    rule_name = Path(__file__).name.split('.')[0]
    r = util.test('http://sg.vegnet.com.cn/News/Detail/1220502', rule_name)
