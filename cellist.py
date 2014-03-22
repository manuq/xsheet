import bisect

class CelList(object):
    def __init__(self):
        self._cels = {}

    def __len__(self):
        return 0

    def __getitem__(self, frame_idx):
        return self.get_relative(frame_idx)

    def __setitem__(self, frame_idx, cel):
        self._cels[frame_idx] = cel

    def __delitem__(self, frame_idx):
        self._cels.pop(frame_idx)

    def get_changing_frames(self):
        return sorted(self._cels.keys())

    def get_until_last_change(self):
        changing_frames = self.get_changing_frames()
        result = []

        for frame, next_frame in zip(changing_frames, changing_frames[1:]):
            result.extend([self._cels[frame]] * (next_frame - frame))

        result.append(self._cels[changing_frames[-1]])

        return result

    def is_unset_at(self, frame_idx):
        return (self[frame_idx] is None or
                frame_idx not in self.get_changing_frames())

    def get_relative(self, frame_idx, cel_diff=0):
        changing_frames = self.get_changing_frames()
        idx = bisect.bisect(changing_frames, frame_idx)
        if idx == 0:
            return None
        if cel_diff == 0:
            return self._cels[changing_frames[idx - 1]]
        if idx - 1 + cel_diff < 0:
            return None
        try:
            return self._cels[changing_frames[idx - 1 + cel_diff]]
        except IndexError:
            return None


__test__ = dict(allem="""

CelList is an infinite list of animation cels.  It is empty after
instantiation.  But unlike List, all indexs are possible.  They return
None.

>>> cels = CelList()
>>> cels[0] == None
True

>>> cels[23] == None
True

>>> cels[-3] == None
True

>>> len(cels) == 0
True

Indexes in CelList are frame numbers.  When a cel is assigned to one
frame, the cel is repeated until None is assigned.

>>> cels[3] = 'b'
>>> cels[3]
'b'

>>> cels[4]
'b'

>>> cels[119]
'b'

>>> cels[2] is None
True

To clear the following frames, assign None.

>>> cels[6] = None
>>> cels[6] is None
True

>>> cels[7] is None
True

>>> cels[119] is None
True

>>> cels[5]
'b'

As said before, CelList are infinite.  Don't try something like this
because it will never end:

# for cel in cels:
#    ...

You can, however, iterate the list until the last change:

>>> cels.get_until_last_change()
['b', 'b', 'b', None]

We can ask the frames where cels change:

>>> cels.get_changing_frames()
[3, 6]

"Is unset" means the cels do not change at the specified frame, or do
change but is None.

>>> cels.is_unset_at(0)
True

>>> cels.is_unset_at(6)
True

Let's add one more cel.

>>> cels[1] = 'a'
>>> cels[1]
'a'

>>> cels.is_unset_at(1)
False

>>> cels.get_until_last_change()
['a', 'a', 'b', 'b', 'b', None]

Fon animation, is important to get the N previous different cel from a
frame, and the next N different cel:

>>> cels.get_relative(4, -1)
'a'

>>> cels.get_relative(4, 1) is None
True

>>> cels.get_relative(2, -1) is None
True

>>> cels.get_relative(2, 1)
'b'

This is how removing works.

>>> del cels[3]

>>> cels.get_until_last_change()
['a', 'a', 'a', 'a', 'a', None]

>>> del cels[3]
Traceback (most recent call last):
KeyError: 3

Another example:

>>> cels = CelList()
>>> cels[0] = 123
>>> cels[2] = 555
>>> cels[12] = 888
>>> cels.get_until_last_change()
[123, 123, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 888]

>>> cels[6] = 232
>>> cels[6]
232

>>> cels.get_until_last_change()
[123, 123, 555, 555, 555, 555, 232, 232, 232, 232, 232, 232, 888]

>>> cels.get_relative(0, -1) is None
True

""")

if __name__ == '__main__':
    import doctest
    doctest.testmod()
