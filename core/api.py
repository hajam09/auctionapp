import json
from http import HTTPStatus

from django.http import JsonResponse
from django.views import View

from core.models import Address, PaymentMethod


class AddressObjectApiEventVersion1Component(View):

    def delete(self, *args, **kwargs):
        body = json.loads(self.request.body)
        Address.objects.filter(**body).delete()
        response = {
            "success": True,
        }
        return JsonResponse(response, status=HTTPStatus.OK)


class PaymentMethodObjectApiEventVersion1Component(View):

    def delete(self, *args, **kwargs):
        body = json.loads(self.request.body)
        PaymentMethod.objects.filter(**body).delete()
        response = {
            "success": True,
        }
        return JsonResponse(response, status=HTTPStatus.OK)