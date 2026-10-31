from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

from .models import SchoolMembership


class SchoolMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = SchoolMembership
        fields = ["id", "user_id", "username", "email", "first_name", "last_name", "role", "is_active", "created_at"]
        read_only_fields = ["id", "user_id", "username", "email", "first_name", "last_name", "created_at"]


class SchoolMemberCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=SchoolMembership.Role.choices)

    def validate_username(self, value):
        User = get_user_model()
        if User._default_manager.filter(username=value).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value
