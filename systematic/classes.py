"""
Common wrapper classes
"""

class SortableContainer(object):
    compare_fields = ()
    def __cmp__(self, other):
        if self.compare_fields:
            for field in self.compare_fields:
                a = getattr(self, field)
                b = getattr(other, field)
                if a != b:
                    return cmp(a, b)

            return 0

        else:
            return cmp(self, other)

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __lte__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __gte__(self, other):
        return self.__cmp__(other) >= 0
