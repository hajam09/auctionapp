import operator
from functools import reduce

from django.db.models import Q

from core.models import Item, Order


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
    filterList = filterListQuerySet(attributesToSearch, filterList, query)
    return Item.objects.filter(reduce(operator.and_, filterList)).distinct()


def performComplexOrderSearch(query, filterList=None):
    filterList = filterList or []
    filterList.append(reduce(operator.or_, [Q(**{'deleteFl': False})]))
    # BUG: Searching doesn't quiet work here properly.
    attributesToSearch = [
        'number', 'tracking', 'item__title', 'item__description', 'item__seller__first_name', 'item__seller__last_name'
    ]

    filterList = filterListQuerySet(attributesToSearch, filterList, query)
    return Order.objects.filter(reduce(operator.and_, filterList)).distinct()


def filterListQuerySet(attributesToSearch, filterList, query):
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
    return filterList
