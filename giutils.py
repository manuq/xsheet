from gi.repository import MyPaint

def brushsetting_from_str(setting_str):
    return getattr(MyPaint.BrushSetting, "SETTING_" + setting_str.upper())

def set_base_value(brush, setting_str, value):
    setting = brushsetting_from_str(setting_str)
    return brush.set_base_value(setting, value)

def get_base_value(brush, setting_str):
    setting = brushsetting_from_str(setting_str)
    return brush.get_base_value(setting)

def set_base_color(brush, color_hsv):
    color_h, color_s, color_v = color_hsv
    set_base_value(brush, "color_h", color_h)
    set_base_value(brush, "color_s", color_s)
    set_base_value(brush, "color_v", color_v)

def get_base_color(brush):
    color_h = get_base_value(brush, "color_h")
    color_s = get_base_value(brush, "color_s")
    color_v = get_base_value(brush, "color_v")
    return color_h, color_s, color_v


__test__ = dict(allem="""

These are auxiliary functions to simplify the API provided by GObject
introspection.

>>> setting = brushsetting_from_str("color_h")
>>> setting == MyPaint.BrushSetting.SETTING_COLOR_H
True

>>> brush = MyPaint.Brush()
>>> set_base_value(brush, "radius_logarithmic", 12.0)
>>> get_base_value(brush, "radius_logarithmic")
12.0

>>> set_base_color(brush, (0.0, 1.0, 0.5))
>>> get_base_color(brush)
(0.0, 1.0, 0.5)

>>> get_base_value(brush, "color_s")
1.0

>>> get_base_value(brush, "color_v")
0.5

""")

if __name__ == '__main__':
    import doctest
    doctest.testmod()
