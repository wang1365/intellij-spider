from template import keys

rule = [
    {
        keys.NAME: 'articles',
        keys.REGEX: [('<li style="background[\s\S]*?</li>', '$0')],
        keys.SEARCH_MODE: '1',
        keys.CHILDREN: [
            {
                keys.NAME: 'type',
                keys.REGEX: [('<span class="lt1">\s*?(.*?)</span>', '$1')],
            },
            {
                keys.NAME: 'title',
                keys.REGEX: [('<span class="lt2">\s*?(.*?)</span>', '$1')],
                keys.REMOVE_HTML: '1',
            },
            {
                keys.NAME: 'date',
                keys.REGEX: [('<span class="lt3">\s*?(.*?)</span>', '$1')],
            },
            {
                keys.NAME: 'articleId',
                keys.REGEX: [('href=".*?/Detail/(\d+)"', '$1')],
            },
            {
                keys.NAME: 'link',
                keys.REGEX: [('href="(.*?)"', 'http://sg.vegnet.com.cn$1')],
                keys.TYPE: '1',
                keys.LINK_RULE: 'sgsc_article'
            },
            {
                keys.NAME: 'articleId',
                keys.REGEX: [('href=".*?/Detail/(\d+)"', '$1')],
            }
        ]
    },
    {
        keys.NAME: keys.VAR_CURRENT_PAGE,
        keys.REGEX: [('<span class="Current">(\d+)', '$1')],
        keys.TYPE: '2'
    },
    {
        keys.NAME: keys.VAR_PAGE_COUNT,
        keys.REGEX: [('.*', '50')],
        keys.TYPE: '2'
    },
    {
        keys.NAME: keys.VAR_PAGE_STEP,
        keys.REGEX: [('.*', '1')],
        keys.TYPE: '2'
    },
    {
        keys.NAME: keys.VAR_PAGE_URL_PATTERN,
        keys.REGEX: [('.*', 'http://sg.vegnet.com.cn/News/List?page={page}')],
        keys.TYPE: '2'
    },
    {
        keys.NAME: 'otherPage',
        keys.TYPE: '3',
        keys.LINK_RULE: 'sgsc_page'
    },
]

if __name__ == '__main__':
    from template import util
    from pathlib import Path

    rule_name = Path(__file__).name.split('.')[0]
    r = util.test('http://sg.vegnet.com.cn/News/List', rule_name)
