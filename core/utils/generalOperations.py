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
    attributesToSearch = ['title', 'description', 'condition']

    if query and query.strip():
        additionalQueryFilter = [
            reduce(
                operator.or_, [
                    Q(**{f'{ats}__icontains': q}) for ats in attributesToSearch
                ]
            )
            for q in query.split()
        ]

        filterList = filterList + additionalQueryFilter

    return Item.objects.filter(reduce(operator.and_, filterList)).distinct()
