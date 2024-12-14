import os

def remove_multiple_suffixes(folder_path, suffixes_to_remove):
    """
    批量去除文件名中多个后缀部分。

    :param folder_path: 文件夹路径
    :param suffixes_to_remove: 要移除的后缀列表
    """
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".html"):
            name, ext = os.path.splitext(file_name)

            for suffix in suffixes_to_remove:
                if suffix in name:
                    name = name.replace(suffix, "")

            name = name.strip()
            old_path = os.path.join(folder_path, file_name)
            new_path = os.path.join(folder_path, name + ext)
            # 如果新文件已存在，则跳过此文件
            if os.path.exists(new_path):
                print(f"跳过: {file_name} -> {name + ext} (文件已存在)")
                continue

            os.rename(old_path, new_path)
            print(f"重命名: {file_name} -> {name + ext}")


# 示例使用
folder_path = './html'  # 替换为实际的文件夹路径
suffixes_to_remove = ['-南开大学', '-多彩校园', '-广播','-南开要闻','-综合新闻','-南开故事','-媒体南开','-南开之声']
remove_multiple_suffixes(folder_path, suffixes_to_remove)
