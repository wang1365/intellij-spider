import datetime
from pathlib import Path
import json
from common.log import logger
import sys
import pathlib

entry_path = pathlib.Path(sys.argv[0])
if entry_path.parent.parent.name != 'apps':
    template_path = '.'
else:
    template_path = 'apps.' + entry_path.parent.name + '.templates.'


def get_rule(name):
    rule_data = None
    try:
        module = __import__(template_path + name, fromlist=[name])
        rule_data = module.rule
    except ModuleNotFoundError as e:
        logger.error('ModuleNotFoundError, Cannot find rule by name. {} {}'.format(name, e))
    return rule_data


def test(url, rule_name):
    from task import Task
    from rule.rule import Rule
    import pprint

    from config import app_config, CacheMode
    app_config.cache_mode = CacheMode.LOCAL_FILE

    printer = pprint.PrettyPrinter(indent=2)
    task = Task(url=url, rule=Rule.find_by_name(rule_name))
    tr = task.execute()
    print('-------------------- 测试结果 --------------------')
    print(tr.data)
    printer.pprint(tr.data)
    print('\n-------------------- 提取链接 --------------------')
    for task in tr.sub_tasks:
        print(task.url, task.rule.name)
    return tr.data


def take_ms(t):
    return (now() - t).microseconds // 1000


def now():
    return datetime.datetime.now()


def today():
    return datetime.date.today()


def now_str():
    return now().strftime('%Y-%m-%d %h:%M:%s')


def today_str():
    return today().strftime('%Y-%m-%d')


def writelines(str_list, file_path: Path):
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open('a', encoding='utf8') as f:
        for data in str_list:
            try:
                f.writelines(json.dumps(data, ensure_ascii=False) + '\n')
            except Exception as e:
                logger.error('!!!!!!!!!!!!!!!!! Write failed, {}'.format(e))
