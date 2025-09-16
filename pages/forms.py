from django import forms
from .models import BusinessRequest, StaticContent

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

class StaticContentForm(forms.ModelForm):
    # Override image_url to use FileField (so you can upload an image)
    image_url = forms.ImageField(required=False)
    required = forms.BooleanField(required=False)

    class Meta:
        model = StaticContent
        fields = ['content_name', 'dimensions', 'image_url', 'required']