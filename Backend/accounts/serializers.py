from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
    )


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
