"""工况映射规则：将报告检验项目与Excel/DB中的condition_name匹配."""

REPORT_ITEMS = [
    {
        "name": "停车D挡工况",
        "conditions": [
            {"keywords": ["停车D档冷风", "停车D挡冷风", "静止低温"], "label": "工况一"},
            {"keywords": ["停车D档暖风", "停车D挡暖风", "静止高温"], "label": "工况二"},
        ]
    },
    {
        "name": "急加速工况",
        "conditions": [
            {"keywords": ["急加速0-100", "零百加速"], "label": "工况一"},
            {"keywords": ["多次加速"], "label": "工况二"},
        ]
    },
    {
        "name": "匀速工况",
        "conditions": [
            {"keywords": ["匀速100冷风", "匀速低温"], "label": "工况一"},
            {"keywords": ["匀速100暖风", "匀速高温"], "label": "工况二"},
        ]
    },
    {
        "name": "超车工况",
        "conditions": [
            {"keywords": ["超车80-140", "超越加速"], "label": "工况一"},
        ]
    },
    {
        "name": "滑行工况",
        "conditions": [
            {"keywords": ["滑行120-40", "D档滑行", "D挡滑行"], "label": "工况一"},
        ]
    },
    {
        "name": "紧急制动工况",
        "conditions": [
            {"keywords": ["急减速120-0", "急刹车120-0", "紧急制动"], "label": "工况一"},
        ]
    },
    {
        "name": "爬坡工况",
        "conditions": [
            {"keywords": ["坡度10_急加速80", "坡度10-急加速80", "急加速80（运动模式）", "急加速80"], "label": "工况一"},
            {"keywords": ["坡度10_匀速80冷风", "坡度10-匀速80冷风", "爬坡低温"], "label": "工况二"},
            {"keywords": ["坡度10_匀速80暖风", "坡度10-匀速80暖风", "爬坡高温"], "label": "工况三"},
        ]
    },
    {
        "name": "停车充电",
        "conditions": [
            {"keywords": ["直流充电冷风"], "label": "工况一"},
            {"keywords": ["直流充电暖风"], "label": "工况二"},
        ]
    },
    {
        "name": "停车充电",
        "conditions": [
            {"keywords": ["交流充电冷风"], "label": "工况一"},
            {"keywords": ["交流充电暖风"], "label": "工况二"},
        ]
    },
]

# 图片插入顺序映射（16张图对应工况关键词）
IMAGE_ORDER = [
    {"keywords": ["停车D档冷风", "停车D挡冷风", "静止低温"], "label": "静止低温"},
    {"keywords": ["停车D档暖风", "停车D挡暖风", "静止高温"], "label": "静止高温"},
    {"keywords": ["急加速0-100", "零百加速"], "label": "零百加速"},
    {"keywords": ["多次加速"], "label": "多次加速"},
    {"keywords": ["匀速100冷风", "匀速低温"], "label": "匀速低温"},
    {"keywords": ["匀速100暖风", "匀速高温"], "label": "匀速高温"},
    {"keywords": ["超车80-140", "超越加速"], "label": "超越加速"},
    {"keywords": ["滑行120-40", "D档滑行", "D挡滑行"], "label": "D挡滑行"},
    {"keywords": ["急减速120-0", "急刹车120-0", "紧急制动"], "label": "紧急制动"},
    {"keywords": ["坡度10_急加速80", "坡度10-急加速80", "急加速80（运动模式）", "急加速80"], "label": "爬坡"},
    {"keywords": ["坡度10_匀速80冷风", "爬坡低温"], "label": "爬坡低温"},
    {"keywords": ["坡度10_匀速80暖风", "爬坡高温"], "label": "爬坡高温"},
    {"keywords": ["直流充电冷风"], "label": "直流充电冷风"},
    {"keywords": ["直流充电暖风"], "label": "直流充电暖风"},
    {"keywords": ["交流充电冷风"], "label": "交流充电冷风"},
    {"keywords": ["交流充电暖风"], "label": "交流充电暖风"},
]


def _match_record(rec: dict, keywords: list[str]) -> bool:
    """检查记录是否匹配任一关键词（同时检查condition_name和condition_id）."""
    cn = rec.get("condition_name", "") or ""
    cid = rec.get("condition_id", "") or ""
    return any(kw in cn or kw in cid for kw in keywords)


def find_report_item_data(item_index: int, records: list[dict]) -> dict:
    """根据检验项目索引，在记录列表中匹配对应工况数据.

    Returns:
        dict: {label: record, ...} 或空dict表示未匹配到
    """
    item = REPORT_ITEMS[item_index]
    result = {}
    for cond in item["conditions"]:
        for rec in records:
            if _match_record(rec, cond["keywords"]):
                result[cond["label"]] = rec
                break
    return result


def find_image_records(records: list[dict]) -> list[dict | None]:
    """按IMAGE_ORDER顺序，从记录列表中匹配16张图片对应的数据记录.

    Returns:
        list: 长度为16，每个元素为匹配到的record或None
    """
    result = []
    for img_map in IMAGE_ORDER:
        matched = None
        for rec in records:
            if _match_record(rec, img_map["keywords"]):
                matched = rec
                break
        result.append(matched)
    return result


def count_matched_items(records: list[dict]) -> int:
    """统计有多少个检验项目至少匹配到一条记录.

    Returns:
        int: 0~9，表示已测工况项目数。
    """
    count = 0
    for item_index in range(len(REPORT_ITEMS)):
        matched = find_report_item_data(item_index, records)
        if matched:
            count += 1
    return count


def count_matched_images(records: list[dict]) -> int:
    """统计匹配到多少张图片（记录非None即可，不检查文件是否存在）.

    Returns:
        int: 0~16，表示有对应数据记录的图片数。
    """
    image_records = find_image_records(records)
    return sum(1 for rec in image_records if rec is not None)
