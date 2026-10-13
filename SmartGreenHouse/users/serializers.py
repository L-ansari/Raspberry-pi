from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only = True,
        min_length = 8,
        style={"input_type":"password"},
    )
    
    class Meta:
        model = User
        fields = ["username","email","password"]
        
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class UserProfileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="pk", read_only = "True")
    
    class Meta:
        model = User
        fields = [
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
        ]