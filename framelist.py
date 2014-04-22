import bisect


class FrameList(object):
    def __init__(self):
        self._values = {}

    def __len__(self):
        return 0

    def __getitem__(self, frame):
        return self.get_relative(frame)

    def __setitem__(self, frame, value):
        self._values[frame] = value

    def __delitem__(self, frame):
        self._values.pop(frame)

    def get_assigned_frames(self):
        return sorted(self._values.keys())

    def get_content_sublist(self):
        changing_frames = self.get_assigned_frames()
        result = []

        for frame, next_frame in zip(changing_frames, changing_frames[1:]):
            result.extend([self._values[frame]] * (next_frame - frame))

        result.append(self._values[changing_frames[-1]])

        return result

    def get_type_at(self, frame, separate_repeats=True):
        value = self[frame]
        assigned_frames = self._values.keys()
        if frame not in assigned_frames:
            if not separate_repeats:
                return "repeat"
            else:
                if value is not None:
                    return "repeat cel"
                else:
                    return "repeat clear"
        else:
            if value is not None:
                return "cel"
            else:
                return "clear"

    def has_cel_at(self, frame):
        return self.get_type_at(frame) == 'cel'

    def has_clear_at(self, frame):
        return self.get_type_at(frame) == 'clear'

    def has_repeat_at(self, frame):
        return self.get_type_at(frame, separate_repeats=False) == 'repeat'

    def has_repeat_cel_at(self, frame):
        return self.get_type_at(frame) == 'repeat cel'

    def has_repeat_clear_at(self, frame):
        return self.get_type_at(frame) == 'repeat clear'

    def get_relative(self, frame, steps=0):
        changing_frames = self.get_assigned_frames()
        idx = bisect.bisect(changing_frames, frame)
        if idx == 0:
            return None
        if steps == 0:
            return self._values[changing_frames[idx - 1]]
        if idx - 1 + steps < 0:
            return None
        try:
            return self._values[changing_frames[idx - 1 + steps]]
        except IndexError:
            return None

    def remove_clear(self, frame):
        if self.has_cel_at(frame) or self.has_clear_at(frame):
            del self[frame]
        else:
            self[frame] = None


__test__ = dict(allem="""

FrameList is an infinite list of animation cels.  In animation, a cel
is a drawing that can be repeated in more than one frame.  The
FrameList is empty after instantiation.  But unlike List, all indexs
are possible.  They return None.

>>> frames = FrameList()
>>> frames[0] == None
True

>>> frames[23] == None
True

>>> frames[-3] == None
True

>>> len(frames) == 0
True

Indexs in FrameList are frame numbers.  When a cel is assigned to one
frame, the cel is repeated until another cel or None is assigned.

>>> frames[3] = 'b'
>>> frames[3]
'b'

>>> frames[4]
'b'

>>> frames[3] == frames[4]
True

>>> frames[119]
'b'

>>> frames[2] is None
True

To clear the following frames, assign None.

>>> frames[6] = None
>>> frames[6] is None
True

>>> frames[7] is None
True

>>> frames[119] is None
True

>>> frames[5]
'b'

We can ask the frames with assigned values, a cel or None:

>>> frames.get_assigned_frames()
[3, 6]

As said before, FrameList are infinite.  Don't try something like this
because it will never end:

# for frame in frames:
#    ...

You can, however, iterate the sublist where frames have content:

>>> frames.get_content_sublist()
['b', 'b', 'b', None]

Note that when we set None to a frame to clear, it belongs to the
assigned frames, unlike other frames with None.

>>> frames[6] is None and frames[7] is None
True

>>> 6 in frames.get_assigned_frames()
True

>>> 7 in frames.get_assigned_frames()
False

There is a shortcut to check if a frame clears:

>>> frames.has_clear_at(6)
True

>>> frames.has_clear_at(7)
False

"Has cel" means there is a cel assigned at the specified frame, and
not None.  So is not a clear or a frame that repeats the previous
assigned value.

>>> frames.has_cel_at(0)
False

>>> frames.has_cel_at(3)
True

>>> frames.has_repeat_at(3)
False

>>> frames.has_cel_at(6)
False

>>> frames.has_repeat_at(6)
False

>>> frames.has_repeat_at(4)
True

>>> frames.has_repeat_cel_at(4)
True

>>> frames.has_repeat_cel_at(3)
False

>>> frames.has_repeat_clear_at(6)
False

>>> frames.has_repeat_clear_at(7)
True

>>> frames.has_repeat_at(7)
True

Frames can contain one of 'cel', 'clear' or 'repeat', so we can ask
the same like this:

>>> frames.get_type_at(0)
'repeat clear'

>>> frames.get_type_at(3)
'cel'

>>> frames.get_type_at(4)
'repeat cel'

>>> frames.get_type_at(6)
'clear'

>>> frames.get_type_at(7)
'repeat clear'

Let's add one more cel.

>>> frames[1] = 'a'
>>> frames[1]
'a'

>>> frames.has_cel_at(1)
True

>>> frames.get_content_sublist()
['a', 'a', 'b', 'b', 'b', None]

Fon animation, is important to get the N previous different cel from a
frame, and the next N different cel:

>>> frames.get_relative(4, steps=-1)
'a'

>>> frames.get_relative(4, steps=1) is None
True

>>> frames.get_relative(2, steps=-1) is None
True

>>> frames.get_relative(2, steps=1)
'b'

>>> frames.get_relative(2, steps=2) is None
True

This is how removing an assigned frame works.

>>> del frames[3]

>>> frames.get_content_sublist()
['a', 'a', 'a', 'a', 'a', None]

You can't remove frames without value, those that repeat the previous
value:

>>> frames[3]
'a'

>>> del frames[3]
Traceback (most recent call last):
KeyError: 3

Is better to use remove_clear.  It will:
- remove the cel, if there is a cel
- mark clear, if the frame repeats
- remove clear, thus repeating, if the frame has clear

>>> frames.remove_clear(3)

>>> frames.get_content_sublist()
['a', 'a', None, None, None, None]

>>> frames.remove_clear(3)

>>> frames.get_content_sublist()
['a', 'a', 'a', 'a', 'a', None]

>>> frames[2] = 'z'

>>> frames.get_content_sublist()
['a', 'z', 'z', 'z', 'z', None]

>>> frames.remove_clear(2)

>>> frames.get_content_sublist()
['a', 'a', 'a', 'a', 'a', None]

Another example:

>>> frames = FrameList()
>>> frames[0] = 123
>>> frames[2] = 555
>>> frames[12] = 888
>>> frames.get_content_sublist()
[123, 123, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 888]

>>> frames[6] = 232
>>> frames[6]
232

>>> frames.get_content_sublist()
[123, 123, 555, 555, 555, 555, 232, 232, 232, 232, 232, 232, 888]

>>> frames.get_relative(0, steps=2)
232

>>> frames.get_relative(6, steps=-2)
123

>>> frames.get_relative(0, steps=-1) is None
True

>>> frames.get_relative(0, steps=8) is None
True

""")


if __name__ == '__main__':
    import doctest
    doctest.testmod()
