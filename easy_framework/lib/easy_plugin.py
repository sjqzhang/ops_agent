# encoding=utf-8


class EasyPlugin (object):
    """
    插件构造函数
    - application 插件所属应用对象
    - name 插件名称
    - config 插件配置
    """
    def __init__(self, application, name, config):
        self.app = application
        self.name = name
        self.config = config
        self.logger = None

    """
    插件初始化方法，加载时自动执行（请在插件子类按需重写）
    """
    def plugin_init(self):
        return 0, 'OK'

    """
    插件处理网络请求方法，框架收到新连接时自动执行
    - session 会话状态管理对象，用于数据收发
    """
    def handle_request(self, session):
        return 0, 'OK'

    """
    插件处理定时事件方法，根据配置定时调用
    """
    def handle_timer(self):
        return 0, 'OK'

    """
    插件处理自定义逻辑方法，当服务类型为customize时调用
    """
    def handle_customize(self):
        return 0, 'OK'

    '''
    构建标准返回包
    '''
    def build_response(self, code, msg, data=None):
        return {'code': code, 'msg': msg, 'data': data}

    """
    插件处理反向连接方法
    """
    def handle_reverse(self, session):
        return 0, 'OK'
