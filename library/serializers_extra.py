from rest_framework import serializers

class ExtendDueDateSerializer(serializers.Serializer):
    additional_days = serializers.IntegerField(min_value=1)