from django import forms
from .models import Store


class StoreForm(forms.ModelForm):
    YES_NO_CHOICES = [
        (True, 'Ja'),
        (False, 'Nee'),
    ]

    image_url = forms.ImageField(
        required=True,
        label="Afbeelding",
        help_text="Upload een logo of banner voor de winkel."
    )
    sale_url = forms.URLField(required=False)
    # image_url = forms.CharField(required=False)  # corresponds to image_url field
    domain_list = forms.JSONField(required=False)
    isVerified = forms.ChoiceField(
        label="Is de mail geverifieerd?",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )

    # NEW #
    isWeirdDomain = forms.ChoiceField(
        label="Was de domein van de email vreemd?",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    # END NEW #

    genderPreferenceSet = forms.ChoiceField(
        label="Moest je man of vrouw aangeven bij de nieuwsbrief?",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
        required=True # You'll likely want this to be a required field
    )
    gender = forms.ChoiceField(
        label="Doelgroep van de winkel",
        choices=Store.GENDER_CHOICES,
        widget=forms.RadioSelect,
        required=True 
    )
    mayUseContent = forms.ChoiceField(
        label = 'Heb je toestemming om de content te gebruiken?',
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )

    class Meta:
        model = Store
        fields = [
            'name',
            'email_addresses',
            'domain',
            'home_url',
            'sale_url',
            'image_url',
            'domain_list',
            'isVerified',
            'genderPreferenceSet',
            'gender',
            'mayUseContent',
            'isWeirdDomain'
        ]
        widgets = {
            'email_addresses': forms.Textarea(attrs={
                'placeholder': 'Typ meerdere e-mailadressen, gescheiden door komma\'s',
                'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super(StoreForm, self).__init__(*args, **kwargs)
        self.fields['sale_url'].required = False
        self.fields['image_url'].required = True
        self.fields['isVerified'].required = True
