from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(help_text="Field errors or additional error context.")


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok"])
    service = serializers.CharField()
    version = serializers.CharField()
