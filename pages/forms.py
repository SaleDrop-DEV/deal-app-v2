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

    class Meta:
        model = StaticContent
        fields = ['content_name', 'dimensions', 'image_url']

    def save(self, commit=True):
        instance = super().save(commit=False)

        # If a file was uploaded, update the image_url with the media path
        uploaded_file = self.cleaned_data.get('image_url')
        if uploaded_file:
            instance.image_url = f"media/{uploaded_file.name}"

        if commit:
            instance.save()
        return instance