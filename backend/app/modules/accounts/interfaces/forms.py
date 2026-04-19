from django import forms


class AccountAddressForm(forms.Form):
    label = forms.CharField(max_length=64, required=True)
    recipient_name = forms.CharField(max_length=150, required=False)
    line_1 = forms.CharField(max_length=255, required=True)
    line_2 = forms.CharField(max_length=255, required=False)
    district = forms.CharField(max_length=120, required=False)
    city = forms.CharField(max_length=120, required=True)
    state = forms.CharField(max_length=64, required=True)
    postal_code = forms.CharField(max_length=16, required=True)
    is_default = forms.BooleanField(required=False)
