from rest_framework import serializers


class MeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.CharField()
    tenant = serializers.CharField()
    tenant_slug = serializers.CharField()
