import sys

VER = sys.version_info[0]


def _check_unicode(val):
    if VER >= 3:
        return isinstance(val, str)
    else:
        return isinstance(val, unicode)

def _is_text(t):
    return isinstance(t, (unicode, str, ) )
