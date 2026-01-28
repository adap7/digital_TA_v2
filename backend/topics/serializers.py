from rest_framework import serializers
from .models import Topic


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "description",
            "order_index",
            "is_published",
            "created_at",
        ]

class TopicCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = [
            "title",
            "description",
            "order_index",
            "is_published",
        ]
