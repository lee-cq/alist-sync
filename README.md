# alist-sync

Alist 同步工具

终极目标：利用GitHub Actions实现使用Github的计算和网络资源定期同步各个网盘之间的数据。

## 预期同步模式：

### 1. copy 简单复制 (已实现)

*命令：* `alist-sync copy -h http://localhost:5244 -u admin -p 123456 -s /源目录 -t /目标目录1 -t /目标目录2 ...`

#### 工作原理：

将源目录中的文件分别同步到全部的目标目录中，

1. 如果目标目录中已经存在该文件，则跳过
2. 忽略存在与目标目录中但不存在于源目录中的文件

### 2. mirror 镜像复制 (已实现)

*命令：* `alist-sync mirror -h http://localhost:5244 -u admin -p 123456 -s /源目录 -t /目标目录1 -t /目标目录2 ...`

#### 工作原理：

将源目录中的文件分别镜像同步到全部的目标目录中，

1. 如果目标目录中已经存在该文件，则跳过
2. 删除存在于目录目录但不存在于源目录中的文件

### 3. sync 多源双向复制（实现中）

*命令：* `alist-sync sync -h http://localhost:5244 -u admin -p 123456 -s /目录1 -s /目录2 -s /目录3 ...`

#### 工作原理：

-s 指定的目录分别作为源目录，想其他的目录中发起copy命令
将源目录中的文件分别镜像同步到全部的目标目录中，

1. 如果目标目录中已经存在该文件，则跳过
2. 删除存在于目录目录但不存在于源目录中的文件

### 4. sync-incr 多源增量复制（设计中）

*命令：* `alist-sync sync_incr -h http://localhost:5244 -u admin -p 123456 -s /目录1 -s /目录2 -s /目录3 ...`

#### 工作原理：

-s 指定的目录分别作为源目录，想其他的目录中发起copy命令, 首次运行后会生成配置文件，持久化保存，作为增量的识别文件。

在每一个需要同步的目录创建.alist-sync-data（它不会被扫描器识别）

    .alist-sync-data/
        scanner/
            time.time.json
        sync-lockor.json
    history/
        file_path_MD5.history
        file_path_MD5.history.json
        ...
