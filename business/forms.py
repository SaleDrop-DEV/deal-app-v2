from django import forms
from .models import SaleMessage, EditProfileRequest

class StoreProfileEditForm(forms.ModelForm):
    """
    A form for business users to edit their store's profile information,
    specifically the description and logo.
    """
    image_url = forms.ImageField(
        label="Nieuw logo (optioneel)",
        required=False
    )
    class Meta:
        model = EditProfileRequest
        fields = ['description', 'image_url']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Vertel iets over je winkel...'}),
        }
        labels = {
            'description': 'Merk omschrijving',
            'image_url': 'Nieuw logo uploaden',
        }
    

class SaleMessageForm(forms.ModelForm):
    """
    A form for business users to create and schedule a new sale message.
    """
    class Meta:
        model = SaleMessage
        fields = ['title', 'grabber', 'description', 'link', 'scheduled_at']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Bijv. Mid-season sale'}),
            'grabber': forms.TextInput(attrs={'placeholder': 'Bijv. Tot 50% korting op alles'}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Beschrijf de sale in meer detail.'}),
            'link': forms.URLInput(attrs={'placeholder': 'https://www.jouwwinkel.nl/sale'}),
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'title': 'Titel van de sale',
            'grabber': 'Pakkende actiezin',
            'description': 'Omschrijving',
            'link': 'Link naar de sale pagina',
            'scheduled_at': 'Verzenddatum (leeglaten om direct te versturen)',
        }