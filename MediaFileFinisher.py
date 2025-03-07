"""此模块用于批量整理媒体文件。"""

import sys
import hashlib
import argparse
import multiprocessing
from multiprocessing.managers import Namespace
from functools import partial
from pathlib import Path, PurePath
from datetime import datetime
from typing import List, Tuple, Dict, Iterable, Optional, Any

from tqdm import tqdm
from hachoir.core import config
from hachoir.core.log import log as logger
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

config.quiet = True


class MediaFileFinisher:
    """媒体文件整理器类。"""

    IMAGE_SUFFIX_FILTER: Tuple = ('.jpg', '.jpeg', '.png')
    VIDEO_SUFFIX_FILTER: Tuple = ('.mp4', '.mov', '.avi', '.dng', '.mp3', '.wmv', '.3gp')

    SUFFIX_FILTER: Tuple = IMAGE_SUFFIX_FILTER + VIDEO_SUFFIX_FILTER

    def __init__(self, src_media_dir: str, dst_media_dir: str):

        self.src_media_dir = Path(src_media_dir)
        self.dst_media_dir = Path(dst_media_dir)

    def is_supported(self, src_media_file: Path) -> bool:
        """
        判断是否为支持的文件类型
        :param src_media_file: Path
        :return: bool
        """

        media_file_suffix: str = Path(src_media_file).suffix

        if src_media_file.is_file():
            if media_file_suffix.lower() in self.SUFFIX_FILTER:
                return True

        return False

    def get_supported_media_file_items(self) -> List[Path]:
        """
        获取支持的媒体文件列表
        :return: List[Path]
        """

        src_media_file_items: Iterable = Path(self.src_media_dir).rglob('*')

        supported_src_media_file_items: List = list(filter(self.is_supported, src_media_file_items))

        return supported_src_media_file_items

    @staticmethod
    def get_media_file_metadata(src_media_file: Path) -> Optional[Dict]:
        """
        获取媒体文件的Metadata数据，以字典格式返回
        :param src_media_file: Path
        :return: Dict or None
        """

        media_file_parser = createParser(str(src_media_file))
        if not media_file_parser:
            logger.warning(f'无法创建媒体文件解析器: {str(src_media_file)}')
            return None

        with media_file_parser:
            try:
                media_file_metadata_raw = extractMetadata(media_file_parser)
                if not media_file_metadata_raw:
                    logger.warning(f'无法提取媒体文件元数据: {str(src_media_file)}')
                    return None
                return media_file_metadata_raw.exportDictionary()
            except (ValueError, TypeError) as e:  # 捕获特定的异常
                logger.warning(f'元数据提取错误: {e}')
                return None

    @staticmethod
    def get_media_file_mtime(src_media_file: Path) -> datetime:
        """
        获取媒体文件的最后修改时间mtime属性，返回datetime对象
        :param src_media_file: Path
        :return: datetime
        """

        media_file_mtime_timestamp = Path(src_media_file).stat().st_mtime
        media_file_creation_time = datetime.fromtimestamp(media_file_mtime_timestamp)
        return media_file_creation_time

    @staticmethod
    def parse_media_time_string(time_string: str) -> Optional[datetime]:
        """
        解析从媒体文件Metadata中获取的时间字符串
        :param time_string: string
        :return: datetime object or None
        """

        datetime_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y/%m/%d %H:%M:%S.%f'
        ]

        for datetime_format in datetime_formats:
            try:
                datetime_obj = datetime.strptime(time_string, datetime_format)
                return datetime_obj
            except ValueError:
                continue  # 尝试下一个格式

        return None  # 所有格式都尝试失败后返回 None

    def get_media_file_creation_time(self, src_media_file: Path) -> datetime:
        """
        获取媒体文件创建时间
        :param src_media_file: Path
        :return: datetime
        """

        media_file_metadata_dict = self.get_media_file_metadata(src_media_file)

        # 如果媒体文件Metadata数据获取失败
        if not media_file_metadata_dict:
            src_media_file_stem: str = PurePath(src_media_file).stem

            # 如果是微信导出的媒体文件，从文件名构建文件创建时间
            if src_media_file_stem.startswith(('mmexport', 'wx_camera')):
                media_file_creation_time_timestamp = int(src_media_file_stem[-12:]) / 1000
                # 将创建时间转换为datetime对象
                media_file_creation_time = datetime.fromtimestamp(
                    media_file_creation_time_timestamp
                )
                return media_file_creation_time

            # 如果已经通过本脚本或者手工格式化过文件名，从文件名构建文件创建时间
            if src_media_file_stem.startswith(('IMG_', 'VID_')) and len(src_media_file_stem) >= 19:
                try:
                    media_file_creation_time_str = src_media_file_stem[4:19]
                    media_file_creation_time = datetime.strptime(
                        media_file_creation_time_str, '%Y%m%d_%H%M%S'
                    )
                    return media_file_creation_time
                except ValueError:
                    logger.warning(f'无法从文件名构建文件创建时间: {str(src_media_file)}')

            # 如果上面两种方式构建失败，则以文件的mtime属性作为文件创建时间
            return self.get_media_file_mtime(src_media_file)

        # 如果媒体文件Metadata数据获取成功
        if media_file_metadata_dict:
            # 尝试获取Metadata的"Date-time original"
            media_file_creation_time_str = (
                media_file_metadata_dict.get('Metadata', {}).get('Date-time original') or
                media_file_metadata_dict.get('Metadata', {}).get('Creation date')
            )

            if not media_file_creation_time_str:
                logger.warning(
                    f'媒体文件{str(src_media_file)}元数据没有"Date-time original"或"Creation date"属性'
                )
                return self.get_media_file_mtime(src_media_file)

            # 解析通过媒体文件Metadata获取的时间字符串
            media_file_creation_time = self.parse_media_time_string(media_file_creation_time_str)
            if not media_file_creation_time:
                return self.get_media_file_mtime(src_media_file)

            # 处理从个别手机APP导出的媒体文件Metadata数据严重不合理的情况
            if media_file_creation_time.year < 2000:
                return self.get_media_file_mtime(src_media_file)

            return media_file_creation_time

        return self.get_media_file_mtime(src_media_file)

    @staticmethod
    def is_duplicated(file1: Path, file2: Path) -> bool:
        """
        判断两个文件是否重复
        :param file1: path of file1
        :param file2: path of file2
        :return: bool
        """

        # 两个文件名为 file1 和 file2，将它们的内容读取到内存中
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            f1_content = f1.read()
            f2_content = f2.read()

        # 计算两个文件的 md5 哈希值
        f1_md5 = hashlib.md5(f1_content).hexdigest()
        f2_md5 = hashlib.md5(f2_content).hexdigest()

        return f1_md5 == f2_md5

    def rename_media_file(self,
                          src_media_file: Path,
                          stats_ns: Namespace,
                          media_file_name_duplicated: Any,
                          media_file_duplicated_removed: Any,
                          lock: Any) -> None:
        """
        执行媒体文件重命名
        :param src_media_file: Path
        :param stats_ns
        :param media_file_name_duplicated
        :param media_file_duplicated_removed
        :param lock
        :return: None
        """

        media_file_creation_time = self.get_media_file_creation_time(src_media_file)
        if media_file_creation_time is None:
            media_file_creation_time = self.get_media_file_mtime(src_media_file)

        # 获取媒体文件创建时间"年月日"字符串，用于构建目的目录名
        src_media_file_creation_date = datetime.strftime(media_file_creation_time, '%Y%m%d')

        # 获取媒体文件创建时间的"年月日_时分秒"字符串，用于构建目的文件名
        src_media_file_creation_time = datetime.strftime(media_file_creation_time, '%Y%m%d_%H%M%S')

        # 获取媒体文件的后缀名
        src_media_file_suffix = Path(src_media_file).suffix

        # 设置媒体文件目录名和文件名的默认值，避免出现空值
        dst_media_file_dir_name = 'UNKNOWN'
        dst_media_file_name = 'UNKNOWN'

        # 构建图片文件的目的目录名和文件名
        if src_media_file_suffix.lower() in self.IMAGE_SUFFIX_FILTER:
            dst_media_file_dir_name = f'PHOTO_{src_media_file_creation_date}'
            dst_media_file_name = (
                f'IMG_{src_media_file_creation_time}'
                f'{src_media_file_suffix.lower()}'
            )

            # 图片文件统计计数
            with lock:
                stats_ns.image_file_nums += 1

        # 构建视频文件的目的目录名和文件名
        if src_media_file_suffix.lower() in self.VIDEO_SUFFIX_FILTER:
            dst_media_file_dir_name = f'VIDEO_{src_media_file_creation_date}'
            dst_media_file_name = (
                f'VID_{src_media_file_creation_time}'
                f'{src_media_file_suffix.lower()}'
            )

            # 视频文件统计计数
            with lock:
                stats_ns.video_file_nums += 1

        # 构建完整的媒体文件目的目录路径Path对象，并自动创建
        dst_media_file_dir = Path.joinpath(self.dst_media_dir, dst_media_file_dir_name)
        if not dst_media_file_dir.exists():
            dst_media_file_dir.mkdir()

        # 构建完整的媒体文件目的路径Path对象
        dst_media_file = Path.joinpath(
            self.dst_media_dir, dst_media_file_dir_name, dst_media_file_name)

        # 如果媒体文件目的路径Path对象不存在，则直接执行移动重命名
        if not dst_media_file.exists():
            src_media_file.rename(dst_media_file)
            logger.info(f'完成 "{str(src_media_file)}" 到 "{str(dst_media_file)}" 的移动重命名')

        # 如果源文件与目的文件完全一致，说明文件重复，直接删除源文件
        elif dst_media_file.exists() and self.is_duplicated(src_media_file, dst_media_file):
            src_media_file.unlink()

            # 媒体文件重复统计计数
            with lock:
                stats_ns.media_file_duplicated_removed_nums += 1

            # 媒体文件重复删除列表
            with lock:
                media_file_duplicated_removed.append(str(src_media_file))

        # 如果媒体文件目的路径Path对象存在，也即出现重复文件名，则在文件名后加一个序号，再执行执行重命名
        else:
            i = 0
            dst_media_file_stem: str = PurePath(dst_media_file).stem
            while True:
                i += 1
                dst_media_file_name = f'{dst_media_file_stem}_{i}{src_media_file_suffix.lower()}'
                dst_media_file = Path.joinpath(
                    self.dst_media_dir, dst_media_file_dir_name, dst_media_file_name)

                # 如果重复文件名出现多次，则每次出现加一个重复序号，直到不出现为止，避免错误覆盖导致文件丢失
                if dst_media_file.exists():
                    if self.is_duplicated(src_media_file, dst_media_file):
                        src_media_file.unlink()
                        # 媒体文件重复统计计数
                        with lock:
                            stats_ns.media_file_duplicated_removed_nums += 1
                        # 媒体文件重复删除列表
                        with lock:
                            media_file_duplicated_removed.append(str(src_media_file))
                        break
                    else:
                        continue
                else:
                    src_media_file.rename(dst_media_file)
                    logger.info(f'完成 "{str(src_media_file)}" 到 "{str(dst_media_file)}" 的移动重命名')

                    # 媒体文件重名统计计数
                    with lock:
                        stats_ns.media_file_name_duplicated_nums += 1

                    # 媒体文件重名列表
                    with lock:
                        media_file_name_duplicated.append(str(dst_media_file))

                    break

    @staticmethod
    def printf(text, *colors) -> None:
        """
        格式化打印带颜色的文本字符
        :param text: string
        :param colors: List or None
        :return:
        """

        esc_code = {'RESET': '0',
                    'BOLD': '1',
                    'BLACK': '30',
                    'RED': '31',
                    'GREEN': '32',
                    'YELLOW': '33',
                    'BLUE': '34'
                    }
        # pylint: disable=line-too-long
        format_text = f"\n\33[{';'.join(esc_code[color] for color in colors)}m{text}\33[{esc_code['RESET']}m"
        sys.stdout.write(format_text)

    def print_stats_data(self,
                         stats_ns,
                         media_file_name_duplicated,
                         media_file_duplicated_removed
                         ) -> None:
        """
        打印统计数据
        :return: None
        """
        self.printf('-' * 20, 'BOLD')
        self.printf('批量重命名媒体文件已完成，统计信息如下:', 'BLUE', 'BOLD')
        self.printf(f'媒体文件总数: {stats_ns.media_file_nums}', 'GREEN')
        self.printf(f'图片文件总数: {stats_ns.image_file_nums}', 'GREEN')
        self.printf(f'视频文件总数: {stats_ns.video_file_nums}', 'GREEN')
        self.printf(f'媒体文件重名数: {stats_ns.media_file_name_duplicated_nums}', 'GREEN')
        self.printf(f'媒体文件重复删除数: {stats_ns.media_file_duplicated_removed_nums}', 'GREEN')

        if media_file_name_duplicated:
            self.printf('-' * 20, 'BOLD')
            self.printf('Media File Name Duplicated:', 'BLUE', 'BOLD')
            for media_file in media_file_name_duplicated:
                self.printf(media_file, 'YELLOW')

        if media_file_duplicated_removed:
            self.printf('-' * 20, 'BOLD')
            self.printf('Media File Duplicated Removed: ', 'BLUE', 'BOLD')
            for media_file in media_file_duplicated_removed:
                self.printf(media_file, 'RED')

    def finish_media_file(self) -> None:
        """
        批量执行媒体文件整理
        :return: None
        """

        supported_src_media_file_items = self.get_supported_media_file_items()
        supported_src_media_file_nums = len(supported_src_media_file_items)

        if not supported_src_media_file_items:
            logger.error(f'源目录 "{self.src_media_dir}" 为空，或者没有支持的媒体文件')
            sys.exit(2)

        # 创建进程池和共享变量
        process_nums = multiprocessing.cpu_count() - 1
        with multiprocessing.Manager() as manager:
            stats_ns = manager.Namespace()
            stats_ns.media_file_nums = supported_src_media_file_nums
            stats_ns.image_file_nums = 0
            stats_ns.video_file_nums = 0
            stats_ns.media_file_name_duplicated_nums = 0
            stats_ns.media_file_duplicated_removed_nums = 0
            media_file_name_duplicated = manager.list()
            media_file_duplicated_removed = manager.list()
            lock = manager.Lock()

            with tqdm(total=supported_src_media_file_nums) as pbar:
                with multiprocessing.Pool(process_nums) as pool:
                    for _, _ in enumerate(pool.imap_unordered(
                        partial(
                            self.rename_media_file,
                            stats_ns=stats_ns,
                            media_file_name_duplicated=media_file_name_duplicated,
                            media_file_duplicated_removed=media_file_duplicated_removed,
                            lock=lock
                        ),
                        supported_src_media_file_items
                    )):
                        pbar.update()

            self.print_stats_data(
                stats_ns,
                media_file_name_duplicated,
                media_file_duplicated_removed
                )

    @classmethod
    def run(cls):
        """
        脚本执行入口
        :return:
        """

        start_time = datetime.now()

        parser = argparse.ArgumentParser(
            prog='MediaFileFinisher.py',
            description='Batch finish media file with format time string.',
            epilog=':-)')
        parser.add_argument('-i', '--input', type=str, required=True,
                            help='Input media file directory path')
        parser.add_argument('-o', '--output', type=str, required=True,
                            help='output media file directory path')
        args = parser.parse_args()

        if not Path(args.input).is_dir():
            logger.error(f'{args.inpout} 不是一个目录.')
            parser.print_help()
            sys.exit(1)
        if not Path(args.output).is_dir():
            logger.error(f'{args.output} 不是一个目录.')
            parser.print_help()
            sys.exit(1)

        mff = cls(args.input, args.output)
        mff.finish_media_file()

        time_usage = datetime.now() - start_time
        cls.printf('-' * 20, 'BOLD')
        cls.printf(f'耗费时间: {time_usage.total_seconds()}s', 'BLUE')


if __name__ == '__main__':

    MediaFileFinisher.run()
