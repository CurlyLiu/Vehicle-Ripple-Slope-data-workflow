"""图片路径解析与验证."""

import os


def resolve_image_path(image_path: str | None) -> str | None:
    """验证并返回有效的图片路径."""
    if not image_path:
        return None
    if os.path.exists(image_path):
        return image_path
    # 尝试转换路径分隔符
    alt_path = image_path.replace("/", os.sep).replace("\\", os.sep)
    if os.path.exists(alt_path):
        return alt_path
    return None
