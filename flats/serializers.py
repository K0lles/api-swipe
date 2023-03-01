from rest_framework.serializers import ModelSerializer

from .models import Addition


class AdditionSerializer(ModelSerializer):

    class Meta:
        model = Addition
        fields = '__all__'
