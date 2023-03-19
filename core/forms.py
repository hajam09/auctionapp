from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from core.models import Item, Image
from core.utils import generalOperations


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        label='',
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Firstname'
            }
        )
    )
    last_name = forms.CharField(
        label='',
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Lastname'
            }
        )
    )
    email = forms.EmailField(
        label='',
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'Email'
            }
        )
    )
    password1 = forms.CharField(
        label='',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Password'
            }
        )
    )
    password2 = forms.CharField(
        label='',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Confirm Password'
            }
        )
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    USERNAME_FIELD = 'email'

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise ValidationError("An account already exists for this email address!")

        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Your passwords do not match!")

        if not generalOperations.isPasswordStrong(password1):
            raise ValidationError("Your password is not strong enough.")

        return password1

    def save(self, save=True):
        user = User()
        user.username = self.cleaned_data.get("email")
        user.email = self.cleaned_data.get("email")
        user.set_password(self.cleaned_data["password1"])
        user.first_name = self.cleaned_data.get("first_name")
        user.last_name = self.cleaned_data.get("last_name")
        user.is_active = settings.DEBUG

        if save:
            user.save()
        return user


class LoginForm(forms.ModelForm):
    email = forms.EmailField(
        label='',
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'Email'
            }
        )
    )
    password = forms.CharField(
        label='',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Password'
            }
        )
    )

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_password(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        user = authenticate(username=email, password=password)
        if user:
            login(self.request, user)
            return self.cleaned_data

        raise ValidationError("Username or Password did not match!")


class DateTimeInput(forms.DateInput):
    input_type = 'datetime-local'


class ItemForm(forms.Form):
    itemName = forms.CharField(
        label='Item Name',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control col',
                'style': 'border-radius: 0',
            }
        )
    )
    description = forms.CharField(
        label='Item Description',
        required=True,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control col',
                'style': 'border-radius: 0',
                'rows': 5,
            }
        )
    )
    condition = forms.ChoiceField(
        label='Item Condition',
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control',
                'style': 'width: 100%; border-radius: 0',
            }
        ),
        choices=Item._meta.get_field('condition').choices,
    )
    expireDate = forms.DateTimeField(
        label='Item End Date/Time (Select if you want to auction this listing)',
        required=False,
        widget=DateTimeInput(
            attrs={
                'class': 'form-control',
                'style': 'width: 100%; border-radius: 0',
            }
        )
    )
    price = forms.DecimalField(
        label='Price (£)',
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'style': 'width: 100%; border-radius: 0',
                'min': '0',
                'step': '.01',
            }
        )
    )
    deliveryCharge = forms.DecimalField(
        label='Delivery Charge (£) - Leave empty if you offer free delivery',
        required=False,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'style': 'width: 100%; border-radius: 0',
                'min': '0',
                'step': '.01',
            }
        )
    )
    stock = forms.IntegerField(
        label='Quantity/stocks you have left',
        required=False,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'style': 'width: 100%; border-radius: 0',
                'min': '1',
                'value': '1',
            }
        )
    )
    images = forms.ImageField(
        label='Upload Item Images',
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control',
                'multiple': 'multiple',
            }
        ),
    )

    def __init__(self, request, item=None, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super(ItemForm, self).__init__(*args, **kwargs)
        self.request = request
        self.item = item

        if item and isinstance(item, Item):
            self.initial['itemName'] = item.title
            self.initial['description'] = item.description
            self.initial['condition'] = Item.Condition[item.condition]
            self.base_fields['expireDate'].initial = item.expireDate.strftime(
                '%Y-%m-%d %H:%M') if item.expireDate else None
            self.base_fields['price'].initial = item.price
            self.base_fields['stock'].initial = item.stock
            self.base_fields['deliveryCharge'].initial = item.deliveryCharge

    def save(self):
        item = Item(
            seller=self.request.user,
            title=self.cleaned_data.get('itemName'),
            description=self.cleaned_data.get('description'),
            expireDate=self.cleaned_data.get('expireDate'),
            price=self.cleaned_data.get('price'),
            deliveryCharge=self.cleaned_data.get('deliveryCharge'),
            type=Item.Type.AUCTION if self.cleaned_data.get('expireDate') else Item.Type.BUY_IT_NOW,
            condition=Item.Condition[self.cleaned_data.get('condition')],
            stock=self.cleaned_data.get('stock')
        )
        item.save()
        Image.objects.bulk_create([Image(item=item, image=i) for i in self.request.FILES.getlist('images')])
        return item

    def update(self):
        self.item.title = self.cleaned_data.get('itemName')
        self.item.description = self.cleaned_data.get('description')
        self.item.expireDate = self.cleaned_data.get('expireDate')
        self.item.price = self.cleaned_data.get('price')
        self.item.deliveryCharge = self.cleaned_data.get('deliveryCharge')
        self.item.type = Item.Type.AUCTION if self.cleaned_data.get('expireDate') else Item.Type.BUY_IT_NOW,
        self.item.condition = Item.Condition[self.cleaned_data.get('condition')]
        self.item.stock = self.cleaned_data.get('stock')
        self.item.save()
        Image.objects.bulk_create([Image(item=self.item, image=i) for i in self.request.FILES.getlist('images')])
        return self.item
