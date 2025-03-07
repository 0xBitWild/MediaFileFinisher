# MediaFileFinisher

MediaFileFinisher 是一个用于批量整理媒体文件（图片和视频）的 Python 工具。它能够根据媒体文件的创建时间自动重命名并分类整理文件，支持多进程处理以提高效率。

## 主要功能

- 自动识别并处理常见图片格式（.jpg、.jpeg、.png）和视频格式（.mp4、.mov、.avi、.dng、.mp3、.wmv、.3gp）
- 智能提取媒体文件的创建时间（按优先级）：
  - 从文件的元数据（Metadata）中提取
  - 从微信导出文件名中提取（支持 mmexport 和 wx_camera 格式）
  - 使用文件的最后修改时间（mtime）作为备选
- 按日期自动分类整理：
  - 图片文件整理到 `PHOTO_YYYYMMDD` 格式的文件夹
  - 视频文件整理到 `VIDEO_YYYYMMDD` 格式的文件夹
- 智能处理重复文件：
  - 自动检测并删除内容完全相同的重复文件
  - 对重名但内容不同的文件自动添加序号
- 多进程并行处理，显著提高处理速度
- 实时进度条显示处理进度
- 详细的统计信息输出

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
python MediaFileFinisher.py -i <输入目录> -o <输出目录>
```

### 参数说明

- `-i, --input`: 待处理的媒体文件源目录
- `-o, --output`: 整理后的媒体文件目标目录

### 使用示例

```bash
python MediaFileFinisher.py -i /path/to/source/media -o /path/to/destination
```

## 输出示例

程序执行完成后会显示详细的统计信息：
- 处理的媒体文件总数
- 图片文件数量
- 视频文件数量
- 重名文件数量
- 重复删除的文件数量
- 重名文件列表
- 被删除的重复文件列表
- 总耗时

## 注意事项

1. 确保对源目录和目标目录有读写权限
2. 建议在处理前备份重要文件
3. 程序会自动跳过不支持的文件格式
4. 对于无法读取创建时间的文件，将使用最后修改时间
5. 重复文件会被自动删除，请谨慎使用

## 系统要求

- Python 3.6+
- 支持多进程的操作系统（Linux/Windows/MacOS）

## 依赖库

- tqdm：进度条显示
- hachoir：媒体文件元数据解析
- typing：类型注解支持

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的媒体文件整理功能
- 实现多进程并行处理
