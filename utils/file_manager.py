import os
import shutil
from typing import List, Optional, Union


class FileManager:
    """文件管理工具类，提供常用的文件和目录操作功能"""

    @staticmethod
    def read_txt_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        读取txt文件内容

        :param file_path: 文件路径
        :param encoding: 编码格式，默认为utf-8
        :return: 文件内容字符串，如果出错则返回None
        """
        try:
            if not FileManager.file_exists(file_path):
                print(f"错误：文件不存在 - {file_path}")
                return None

            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()

        except UnicodeDecodeError:
            print(f"错误：读取文件时编码错误 - {file_path}，尝试使用其他编码")
            return None
        except Exception as e:
            print(f"错误：读取文件失败 - {str(e)}")
            return None

    @staticmethod
    def write_txt_file(file_path: str, content: str, encoding: str = 'utf-8',
                       overwrite: bool = True) -> bool:
        """
        写入内容到txt文件

        :param file_path: 文件路径
        :param content: 要写入的内容
        :param encoding: 编码格式，默认为utf-8
        :param overwrite: 是否覆盖已有文件，True为覆盖，False为追加
        :return: 操作是否成功
        """
        try:
            # 确保目录存在
            dir_path = os.path.dirname(file_path)
            if dir_path and not FileManager.dir_exists(dir_path):
                FileManager.create_dir(dir_path)

            mode = 'w' if overwrite else 'a'
            with open(file_path, mode, encoding=encoding) as file:
                file.write(content)
            return True

        except Exception as e:
            print(f"错误：写入文件失败 - {str(e)}")
            return False

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        删除文件

        :param file_path: 要删除的文件路径
        :return: 操作是否成功
        """
        try:
            if not FileManager.file_exists(file_path):
                print(f"警告：文件不存在，无法删除 - {file_path}")
                return False

            os.remove(file_path)
            return True

        except PermissionError:
            print(f"错误：没有权限删除文件 - {file_path}")
            return False
        except Exception as e:
            print(f"错误：删除文件失败 - {str(e)}")
            return False

    @staticmethod
    def copy_file(src_path: str, dest_path: str, overwrite: bool = False) -> bool:
        """
        复制文件

        :param src_path: 源文件路径
        :param dest_path: 目标文件路径
        :param overwrite: 如果目标文件存在，是否覆盖
        :return: 操作是否成功
        """
        try:
            if not FileManager.file_exists(src_path):
                print(f"错误：源文件不存在 - {src_path}")
                return False

            if FileManager.file_exists(dest_path) and not overwrite:
                print(f"警告：目标文件已存在，未执行复制 - {dest_path}")
                return False

            # 确保目标目录存在
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not FileManager.dir_exists(dest_dir):
                FileManager.create_dir(dest_dir)

            shutil.copy2(src_path, dest_path)  # 保留元数据
            return True

        except Exception as e:
            print(f"错误：复制文件失败 - {str(e)}")
            return False

    @staticmethod
    def move_file(src_path: str, dest_path: str, overwrite: bool = False) -> bool:
        """
        移动文件

        :param src_path: 源文件路径
        :param dest_path: 目标文件路径
        :param overwrite: 如果目标文件存在，是否覆盖
        :return: 操作是否成功
        """
        try:
            if not FileManager.file_exists(src_path):
                print(f"错误：源文件不存在 - {src_path}")
                return False

            if FileManager.file_exists(dest_path):
                if overwrite:
                    FileManager.delete_file(dest_path)
                else:
                    print(f"警告：目标文件已存在，未执行移动 - {dest_path}")
                    return False

            # 确保目标目录存在
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not FileManager.dir_exists(dest_dir):
                FileManager.create_dir(dest_dir)

            shutil.move(src_path, dest_path)
            return True

        except Exception as e:
            print(f"错误：移动文件失败 - {str(e)}")
            return False

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """检查文件是否存在"""
        return os.path.isfile(file_path)

    @staticmethod
    def dir_exists(dir_path: str) -> bool:
        """检查目录是否存在"""
        return os.path.isdir(dir_path)

    @staticmethod
    def create_dir(dir_path: str, recursive: bool = True) -> bool:
        """
        创建目录

        :param dir_path: 目录路径
        :param recursive: 是否创建多级目录
        :return: 操作是否成功
        """
        try:
            if not FileManager.dir_exists(dir_path):
                os.makedirs(dir_path, exist_ok=recursive)
            return True
        except Exception as e:
            print(f"错误：创建目录失败 - {str(e)}")
            return False

    @staticmethod
    def delete_dir(dir_path: str, recursive: bool = False) -> bool:
        """
        删除目录

        :param dir_path: 目录路径
        :param recursive: 是否递归删除（删除目录及其所有内容）
        :return: 操作是否成功
        """
        try:
            if not FileManager.dir_exists(dir_path):
                print(f"警告：目录不存在，无法删除 - {dir_path}")
                return False

            if recursive:
                shutil.rmtree(dir_path)
            else:
                os.rmdir(dir_path)  # 只能删除空目录
            return True

        except PermissionError:
            print(f"错误：没有权限删除目录 - {dir_path}")
            return False
        except OSError as e:
            print(f"错误：删除目录失败，可能目录非空 - {str(e)}")
            return False
        except Exception as e:
            print(f"错误：删除目录失败 - {str(e)}")
            return False

    @staticmethod
    def list_dir(dir_path: str, include_files: bool = True, include_dirs: bool = True) -> List[str]:
        """
        列出目录内容

        :param dir_path: 目录路径
        :param include_files: 是否包含文件
        :param include_dirs: 是否包含子目录
        :return: 目录内容列表
        """
        try:
            if not FileManager.dir_exists(dir_path):
                print(f"错误：目录不存在 - {dir_path}")
                return []

            items = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path) and include_files:
                    items.append(item_path)
                elif os.path.isdir(item_path) and include_dirs:
                    items.append(item_path)

            return items

        except Exception as e:
            print(f"错误：列出目录内容失败 - {str(e)}")
            return []


# 使用示例
if __name__ == "__main__":
    # 创建文件管理器实例
    fm = FileManager()

    # 示例文件路径
    test_file = "test.txt"
    test_dir = "test_dir"
    copy_file = os.path.join(test_dir, "test_copy.txt")

    # 写入文件
    fm.write_txt_file(test_file, "这是一个测试文件\n用于演示文件管理工具类的功能")

    # 读取文件
    content = fm.read_txt_file(test_file)
    if content:
        print("文件内容：")
        print(content)

    # 创建目录
    fm.create_dir(test_dir)

    # 复制文件
    fm.copy_file(test_file, copy_file, overwrite=True)

    # 列出目录内容
    print("\n目录内容：")
    for item in fm.list_dir(test_dir):
        print(item)

    # 移动文件（重命名）
    fm.move_file(copy_file, os.path.join(test_dir, "test_rename.txt"))

    # 清理测试文件和目录
    fm.delete_file(test_file)
    fm.delete_dir(test_dir, recursive=True)

    print("\n操作完成")
