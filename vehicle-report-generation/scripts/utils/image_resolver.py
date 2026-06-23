"""图片路径解析与验证."""

import os
import re


def resolve_image_path(image_path: str | None) -> str | None:
    """验证并返回有效的图片路径.

    兼容历史数据中可能出现的错误盘符（如 F:\Vehicle_Date -> E:\Vehicle_Date）。
    """
    if not image_path:
        return None
    candidates = [
        image_path,
        image_path.replace("/", os.sep).replace("\\", os.sep),
    ]
    # 若路径指向不存在的盘符但项目目录结构相同，尝试其他常见盘符
    drive_match = re.match(r'^([A-Za-z]:)(\\\\|\\)?', image_path)
    if drive_match:
        original_drive = drive_match.group(1)
        for drive in ["E:", "D:", "C:", "F:", "G:"]:
            if drive.upper() == original_drive.upper():
                continue
            alt_drive_path = re.sub(
                r'^' + re.escape(original_drive) + r'(\\\\|\\)?',
                drive + r'\\',
                image_path,
                count=1,
            )
            candidates.append(alt_drive_path)
            candidates.append(alt_drive_path.replace("/", os.sep).replace("\\", os.sep))

    for path in candidates:
        if os.path.exists(path):
            return path
    return None
