import operator
from functools import reduce

from django.db.models import Q

from core.models import Item


def isPasswordStrong(password):
    if len(password) < 8:
        return False

    if not any(letter.isalpha() for letter in password):
        return False

    if not any(capital.isupper() for capital in password):
        return False

    if not any(number.isdigit() for number in password):
        return False

    return True


def performComplexItemSearch(query, filterList=None):
    filterList = filterList or []
    filterList.append(reduce(operator.or_, [Q(**{'deleteFl': False})]))
    attributesToSearch = ['title', 'description']

    if query and query.strip():
        filterList.append(reduce(operator.or_, [Q(**{f'{v}__icontains': query}) for v in attributesToSearch]))

    return Item.objects.filter(reduce(operator.and_, filterList)).distinct()
