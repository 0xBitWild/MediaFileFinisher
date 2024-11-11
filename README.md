# MediaFileFinisher

一个以时间为维度批量快速整理视频和图片文件的脚本。

# 功能

- 使用hachoir库提取媒体文件Metadata中时间数据；
- 从微信导出的文件，通过文件名提取时间戳数据；
- 时间戳信息完全一致的媒体文件，自动进行重名处理了；
- 只有重名，且MD5信息相同的文件才会被自动去重删除；
- 执行完成后，输出统计信息；


# 使用方法


```bash

# 克隆项目
git clone https://github.com/0xBitwild/MediaFileFinisher.git

# 进入项目目录
cd MediaFileFinisher

# 配置虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python MediaFileFinisher.py -i /path/to/input/dir -o /path/to/output/dir

```
