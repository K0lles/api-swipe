from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import ModelSerializer, ImageField, PrimaryKeyRelatedField

from .fields import AdditionField

from .models import *
from users.serializers import AuthRegistrationSerializer


class PhotoSerializer(ModelSerializer):
    id = IntegerField(required=False, write_only=False)
    photo = ImageField()

    class Meta:
        model = Photo
        exclude = ['gallery']


class AdditionSerializer(ModelSerializer):

    class Meta:
        model = Addition
        fields = '__all__'


class AdditionInComplexSerializer(ModelSerializer):
    id = IntegerField(required=False, write_only=False)
    addition = AdditionField(required=True)

    class Meta:
        model = AdditionInComplex
        fields = ['id', 'addition', 'turned_on']

    def create(self, validated_data):
        addition = AdditionInComplex.objects.create(
            residential_complex=self.context.get('residential_complex'),
            **validated_data
        )
        return addition


class CorpsSerializer(ModelSerializer):
    name = CharField(read_only=True)

    class Meta:
        model = Corps
        exclude = ['residential_complex']


class DocumentSerializer(ModelSerializer):
    residential_complex = PrimaryKeyRelatedField(queryset=ResidentialComplex.objects.all(), required=False)

    class Meta:
        model = Document
        fields = '__all__'

    def validate(self, attrs):
        if attrs.get('residential_complex', None) is None:
            if self.context.get('residential_complex', None) is None:
                raise ValidationError({'residential_complex': [_('Не вказано ЖК.')]})
            attrs['residential_complex'] = self.context.get('residential_complex')
        return super().validate(attrs)

    def create(self, validated_data):
        instance = Document.objects.create(
            **validated_data,
        )
        return instance

    def update(self, instance, validated_data):
        for field in validated_data:
            setattr(instance, field, validated_data.get(field))
        instance.save()
        return instance


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
                owner=self.context.get('user'),
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

    def update(self, instance: ResidentialComplex, validated_data: dict):
        additions = validated_data.pop('additions', None)
        gallery = validated_data.pop('gallery_photos', None)

        for key in validated_data.keys():
            setattr(instance, key, validated_data.get(key))

        instance.save()

        remove_items_additions = {item.id: item for item in instance.additionincomplex_set.all()}
        remove_items_gallery = {item.id: item for item in instance.gallery.photo_set.all()}

        for item in additions:
            item_id = item.get('id', None)

            if not item_id:
                AdditionInComplex.objects.create(
                    residential_complex=instance,
                    addition=item.get('addition'),
                    turned_on=item.get('turned_on')
                )
            elif remove_items_additions.get(item_id, None) is not None:
                item_instance = remove_items_additions.pop(item_id, None)
                AdditionInComplex.objects.filter(id=item_instance.id).update(**item)

        for item in gallery:
            item_id = item.get('id', None)

            if not item_id:
                Photo.objects.create(gallery=instance.gallery, **item)
            elif remove_items_gallery.get(item_id, None) is not None:
                item_instance = remove_items_gallery.pop(item_id, None)
                Photo.objects.filter(id=item_instance.id).update(**item)

        return instance

    def to_representation(self, instance: ResidentialComplex):
        data = super().to_representation(instance=instance)
        data.update(
            {
                'gallery_photos': PhotoSerializer(instance=instance.gallery.photo_set.all(), many=True).data,
                'additions': AdditionInComplexSerializer(instance=instance.additionincomplex_set.all(), many=True).data
             }
        )
        return data
