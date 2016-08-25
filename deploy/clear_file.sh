#目录                #阀值        #命令  #参数 #目标
log                  70%:200M    delete    7    *.log.*
easyAgent/log        70%:200M    delete    7    *.log.*
collector_agent/log  70%:200M    delete    7    *.log.*

#----说明-----
#目录：需要监控的目录，使用相对安装目录路径
#阀值：触发清理操作的条件[分区使用百分比:目录最大空间<M|m>]
#命令：delete(删除指定时间前文件)，tar(压缩指定时间前文件)，clear(清空超过指定大小文件)
#参数：delete,tar(默认天数,后缀h为小时，m为分钟)，clear(文件大小k)
#目标：可以清理的文件,接受通配符

#----示例-----
#目录     #阀值    #命令   #参数  #目标
#log      80%:10M  delete  30     stat*.log
#data     90%:10M  tar     30     */*.dat
#log      90%:10M  clear   50000  debug/err*.log