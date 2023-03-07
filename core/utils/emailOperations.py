from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def sendEmailToActivateAccount(request, user: User):
    if settings.DEBUG or user.is_active:
        return

    currentSite = get_current_site(request)
    emailSubject = "Activate your OneAuction Account"
    fullName = user.get_full_name()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    prtg = PasswordResetTokenGenerator()
    url = reverse('accounts:activate-account', kwargs={'encodedId': uid, "token": prtg.make_token(user)})

    message = """
        Hi {},
        \n
        Welcome to OneAuction, thank you for your joining our service.
        We have created an account for you to unlock more features.
        \n
        please click this link below to verify your account
        http://{}{}
        \n
        Thanks,
        The OneAuction Team
    """.format(fullName, currentSite.domain, url)

    emailMessage = EmailMessage(emailSubject, message, settings.EMAIL_HOST_USER, [user.email])
    emailMessage.send()
    return