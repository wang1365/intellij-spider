def get_rule(name):
    rule_data = None
    try:
        module = __import__('templates.' + name, fromlist=(name))
        rule_data = module.rule
    except ModuleNotFoundError as e:
        print('ModuleNotFoundError, Cannot find rule by name', name, e)
    return rule_data


def test(url, rule_name):
    from task import Task
    from rule.rule import Rule
    import pprint

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