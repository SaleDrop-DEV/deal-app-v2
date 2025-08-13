from django import forms
from .models import BusinessRequest

class BusinessRequestForm(forms.ModelForm):
    message = forms.CharField(
        max_length=225,
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}), # Use a Textarea for a better user experience
    )

    class Meta:
        # Specifies the model to use.
        model = BusinessRequest
        fields = ['store_name', 'store_email', 'store_phone_number', 'message']

