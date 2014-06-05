"""
Common wrapper classes
"""

class SortableContainer(object):
    """Sortable containers 

    Sort objects by comparing attributes specified in 
    tuple self.compare_fields

    List of attributes must match for compared objects or
    comparison will fail.

    """

    compare_fields = ()
    
    def __cmp__(self, other):
        if self.compare_fields:
            for field in self.compare_fields:
                a = getattr(self, field)
                b = getattr(other, field)
                if a != b:
                    return cmp(a, b)

            return 0

        return cmp(self, other)

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0
