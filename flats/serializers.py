from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, ImageField

from .fields import AdditionField

from .models import Addition, ResidentialComplex, AdditionInComplex, Gallery, Photo
from users.serializers import AuthRegistrationSerializer


class PhotoSerializer(ModelSerializer):
    photo = ImageField()

    class Meta:
        model = Photo
        exclude = ['gallery']


class AdditionSerializer(ModelSerializer):

    class Meta:
        model = Addition
        fields = '__all__'


class AdditionInComplexSerializer(ModelSerializer):
    addition = AdditionField(required=True)

    class Meta:
        model = AdditionInComplex
        fields = ['id', 'addition', 'turned_on']


class ResidentialComplexSerializer(ModelSerializer):
    photo = ImageField()
    owner = AuthRegistrationSerializer(read_only=True)
    additions = AdditionInComplexSerializer(many=True, required=False)
    gallery_photos = PhotoSerializer(many=True, required=False)

    class Meta:
        model = ResidentialComplex
        exclude = ['gallery']

    def create(self, validated_data: dict):
        additions = validated_data.pop('additions', None)
        gallery = validated_data.pop('gallery_photos', None)
        try:
            residential_complex = ResidentialComplex.objects.create(
                owner=self.context.get('request').user,
                gallery=Gallery.objects.create(),
                **validated_data
            )
        except IntegrityError:
            raise ValidationError({"detail": _("You already have residential complex")})

        if additions:
            for addition in additions:
                AdditionInComplex.objects.create(
                    residential_complex=residential_complex,
                    addition=addition.get('addition'),
                    turned_on=addition.get('turned_on')
                )

        if gallery:
            for photo in gallery:
                Photo.objects.create(
                    photo=photo.get('photo'),
                    gallery=residential_complex.gallery,
                    sequence_number=photo.get('sequence_number')
                )

        return residential_complex

    def to_representation(self, instance: ResidentialComplex):
        data = super().to_representation(instance=instance)
        data.update(
            {
                'gallery_photos': PhotoSerializer(instance=instance.gallery.photo_set.all(), many=True).data,
                'additions': AdditionInComplexSerializer(instance=instance.additionincomplex_set.all(), many=True).data
             }
        )
        return data
