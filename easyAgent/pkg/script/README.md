### 原agent的pkg目录，将其独立出来。给所有组件提供：
* 配置目录初始化（init）
* 进程启停（start、stop、restart）
* 进程监控（自定义监控）
* 端口监控
* crontab
* 日志清理

该能力的输出统一由easyops命令提供：

```
[root@publicDev_1 php]# easyops -h
usage: easyops.py [-h] [--pkg_id PKG_ID] [--debug]
                  {start,stop,restart,uninstall,monitor,init,which}
                  [app_folder]

run process which deploy by easyops

positional arguments:
  {start,stop,restart,uninstall,monitor,init,which}
                        action choices
  app_folder            the app folder(default: current folder)

optional arguments:
  -h, --help            show this help message and exit
  --pkg_id PKG_ID       pkg_id for init action, you can pass packageId from
                        CMDB(default: app folder name)
  --debug               debug output
```

