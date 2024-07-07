import re
import time


def get_time():
    """
    获取当前时间戳

    Get the current timestamp
    :return:
        int(time)
    """
    return int(round(time.time()))


def remove_duplicates_2d_array(arr):
    seen = []
    result = []
    for sub_array in arr:
        if sub_array not in seen:
            result.append(sub_array)
            seen.append(sub_array)
    return result


def xml_escape(title):
    # XML
    title = str(title).replace("&", r"&amp;").replace("<", r"&lt;").replace(">", "&gt;").replace('"', "&quot;").replace(
        "'", "&apos;")
    return title


def windows_escape(title):
    return re.sub(r'''[\\/:*?"<>|]''', '', title)
