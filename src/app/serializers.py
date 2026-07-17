from rest_framework import serializers

from app.models.assessment import PoemAssessment
from app.models.author import Author
from app.models.poem import Poem


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = [
            "id",
            "name",
            "email",
        ]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class TokenRefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class PoemCreateSerializer(serializers.Serializer):
    content = serializers.CharField(trim_whitespace=False)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class PoemUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, trim_whitespace=False)
    comment = serializers.CharField(required=False, allow_blank=True)


class PoemListQuerySerializer(serializers.Serializer):
    collection = serializers.IntegerField(required=False, allow_null=True, default=None)
    query = serializers.CharField(required=False, allow_blank=True, default="")


class PoemAssessmentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoemAssessment
        fields = [
            "freshness",
            "emotional_density",
            "voice",
            "completeness",
            "anti_repeat",
            "comment",
            "model_name",
        ]


class PoemSerializer(serializers.ModelSerializer):
    assessment = PoemAssessmentNestedSerializer(read_only=True)

    class Meta:
        model = Poem
        fields = [
            "id",
            "title",
            "content",
            "comment",
            "assessment",
        ]
