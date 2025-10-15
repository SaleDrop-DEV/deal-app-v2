from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.conf import settings
from django.urls import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator


from accounts.models import ExtraUserInformation



User = get_user_model()

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD  # make sure EMAIL_FIELD is set correctly in your user model

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = User.objects.filter(email=email).first()
        if not user.is_active:
            raise serializers.ValidationError({"error": "Account is niet geactiveerd, check je e-mail of spam."})

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                username=email, password=password)
            if not user:
                print("Invalid user")
                raise serializers.ValidationError({"error": "Ongeldige email of wachtwoord."})

            if not user.is_active:
                print("User account is disabled")
                raise serializers.ValidationError({"error": "Account is ongeldig."})

        else:
            raise serializers.ValidationError({"error": "Voer een email en wachtwoord in."})
        print("Validated")

        refresh = self.get_token(user)

        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return data


# Get the custom user model
CustomUser = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for the user registration endpoint.
    It handles validation for email and password.
    """
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=CustomUser.objects.all())]
    )
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    gender = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'password', 'password2', 'gender')

    def validate(self, attrs):
        """
        Check that the two password fields match.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Wachtwoorden komen niet overeen."})
        valid_genders = ['man', 'vrouw', 'anders']
        if attrs['gender'] not in valid_genders:
            raise serializers.ValidationError({"gender": "Ongeldige waarde voor geslacht."})
        return attrs

    def create(self, validated_data):
        """
        Create and return a new CustomUser instance, given the validated data.
        Also attempts to send a verification email.
        """
        # Remove password2 as it's not a model field
        
        gender_map = {
            'man': 0,
            'vrouw': 1,
            'anders': 2
        }
        gender_str = validated_data.pop('gender')
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False
        )
        gender_int = gender_map.get(gender_str)
        ExtraUserInformation.objects.create(user=user, gender=gender_int)
        
        mail_subject = 'Activeer je account.'

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        # You must include the protocol (http or https)
        base_activation_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        activation_link = f"{settings.CURRENT_URL}{base_activation_url}?source=app"

        message = render_to_string('email/validation_email.html', {
            'user': user,
            'uid': uid,
            'token': token,
            'activation_link': activation_link,
        })
        to_email = validated_data['email']

        try:
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.content_subtype = "html"
            email.send()
            self.verification_email_sent = True  # Set to True on success
        except Exception as e:
            print(f"Error sending verification email: {e}")
            self.verification_email_sent = False # Set to False on failure
        return user


class UserRegistrationSerializerV2(serializers.ModelSerializer):
    """
    Serializer for the user registration endpoint.
    It handles validation for email and password.
    """
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=CustomUser.objects.all())]
    )
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    gender = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'password', 'password2', 'gender')

    def validate(self, attrs):
        """
        Check that the two password fields match.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Wachtwoorden komen niet overeen."})
        valid_genders = ['man', 'vrouw', 'anders']
        if attrs['gender'] not in valid_genders:
            raise serializers.ValidationError({"gender": "Ongeldige waarde voor geslacht."})
        return attrs

    def create(self, validated_data):
        """
        Create and return a new CustomUser instance, given the validated data.
        Also attempts to send a verification email.
        """
        # Remove password2 as it's not a model field
        
        gender_map = {
            'man': 0,
            'vrouw': 1,
            'anders': 2
        }
        gender_str = validated_data.pop('gender')
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False
        )
        gender_int = gender_map.get(gender_str)
        ExtraUserInformation.objects.create(user=user, gender=gender_int)
        
        mail_subject = 'Activeer je account.'

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        # You must include the protocol (http or https)
        base_activation_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        activation_link = f"{settings.CURRENT_URL}{base_activation_url}?source=appV2"

        message = render_to_string('email/validation_email.html', {
            'user': user,
            'uid': uid,
            'token': token,
            'activation_link': activation_link,
        })
        to_email = validated_data['email']

        try:
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.content_subtype = "html"
            email.send()
            self.verification_email_sent = True  # Set to True on success
        except Exception as e:
            print(f"Error sending verification email: {e}")
            self.verification_email_sent = False # Set to False on failure
        return user

