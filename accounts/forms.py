from django import forms
from django.contrib.auth import get_user_model
from .models import ExtraUserInformation


# Get the custom user model that's active in your settings
CustomUser = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    """
    A custom form for creating a CustomUser with email as the primary field.
    It no longer inherits from UserCreationForm.
    """
    # Define the two password fields explicitly
    password = forms.CharField(
        label="Wachtwoord",
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Herhaal wachtwoord",
        widget=forms.PasswordInput
    )
    
    # Add gender field
    gender = forms.ChoiceField(
        label="Geslacht",
        choices=ExtraUserInformation.GENDER_CHOICES,
        widget=forms.RadioSelect
    )

    class Meta:
        # Use the custom user model instead of the default User model
        model = CustomUser
        fields = ['email'] # Only include the email field from the model
    
    def clean(self):
        """
        Validate that the two password fields match.
        """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        gender = cleaned_data.get("gender")

        if not gender:
            self.add_error('gender', 'Geslacht is verplicht.')
        else:
            print(f"gender: {gender}")
            cleaned_data['gender'] = gender
        
        if password and password2 and password != password2:
            # Raise a form-wide validation error if they don't match
            self.add_error('password2', 'Wachtwoorden komen niet overeen.')

        return cleaned_data
        
        
    def save(self, commit=True):
        """
        Create and save the user and the related ExtraUserInformation object.
        """
        # Create the user object from the form data
        user = super().save(commit=False)
        # Set the hashed password from the form's password field
        user.set_password(self.cleaned_data["password"])
        
        if commit:
            user.save()
            # Save ExtraUserInformation with selected gender
            gender_value = self.cleaned_data.get('gender')
            print(f"gender_value: {gender_value}")
            ExtraUserInformation.objects.create(
                user=user,
                gender=gender_value
            )

        return user


    def save_old(self, commit=True):
        """
        Create and save the user and the related ExtraUserInformation object.
        """
        # Create the user object from the form data
        user = super().save(commit=False)
        # Set the hashed password from the form's password field
        user.set_password(self.cleaned_data["password"])
        
        if commit:
            user.save()
            # Save ExtraUserInformation with selected gender
            gender_value = self.cleaned_data.get('gender')
            print(f"gender_value: {gender_value}")
            ExtraUserInformation.objects.create(
                user=user,
                gender=gender_value
            )

        return user

class GenderPreferenceForm(forms.ModelForm):
    class Meta:
        model = ExtraUserInformation
        fields = ['gender']
        labels = {
            'gender': 'Voorkeur',
        }
        widgets = {
            'gender': forms.RadioSelect(choices=[
                (0, 'Man'),
                (1, 'Vrouw'),
                (2, 'Anders'),
            ]),
        }



from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

# Get your custom user model
CustomUser = get_user_model()

class CustomAuthenticationForm(AuthenticationForm):
    # This field will be the email address, but we'll call it 'username' for the form's internal logic.
    username = forms.EmailField(
        label="E-mailadres",
        widget=forms.TextInput(attrs={'autofocus': True})
    )


    def clean(self):
        # Get the submitted email and password from the form's cleaned data.
        email = self.cleaned_data.get('username')
        print(email)
        password = self.cleaned_data.get('password')


        if email and password:
            # Use the authenticate function to check the credentials.
            # We explicitly pass the email instead of a username.
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                # If authentication fails, raise a validation error.
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
        return self.cleaned_data
