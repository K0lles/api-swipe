from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import ModelSerializer, ImageField, PrimaryKeyRelatedField

from drf_extra_fields.fields import Base64ImageField

from .fields import AdditionField, ResidentialComplexDisplayField, FlatSquarePriceField

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
    residential_complex = ResidentialComplexDisplayField(read_only=True)

    class Meta:
        model = Corps
        fields = '__all__'


class CorpsInResidentialSerializer(ModelSerializer):

    class Meta:
        model = Corps
        exclude = ['residential_complex']

    def to_representation(self, instance: Corps):
        data = super().to_representation(instance)
        data.update(
            {
                'flat_amount': instance.flat_set.all().count()
            }
        )
        return data


class SectionSerializer(ModelSerializer):
    name = CharField(read_only=True)
    residential_complex = ResidentialComplexDisplayField(read_only=True)

    class Meta:
        model = Section
        fields = '__all__'


class DocumentSerializer(ModelSerializer):
    residential_complex = PrimaryKeyRelatedField(queryset=ResidentialComplex.objects.all(), required=False)

    class Meta:
        model = Document
        fields = '__all__'

    def validate(self, attrs):
        if attrs.get('residential_complex', None) is None:
            if self.context.get('residential_complex', None) is None and not self.instance:
                raise ValidationError({'residential_complex': [_('Не вказано ЖК.')]})
            if not self.instance:
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


class DocumentDisplaySerializer(ModelSerializer):

    class Meta:
        model = Document
        exclude = ['residential_complex']


class NewsSerializer(ModelSerializer):
    residential_complex = PrimaryKeyRelatedField(queryset=ResidentialComplex.objects.all(), required=False)

    class Meta:
        model = News
        fields = '__all__'

    def validate(self, attrs):
        if attrs.get('residential_complex', None) is None:
            if self.context.get('residential_complex', None) is None and not self.instance:
                raise ValidationError({'residential_complex': [_('Не вказано ЖК.')]})
            if not self.instance:
                attrs['residential_complex'] = self.context.get('residential_complex')
        return super().validate(attrs)

    def create(self, validated_data):
        instance = News.objects.create(
            **validated_data,
        )
        return instance

    def update(self, instance, validated_data):
        for field in validated_data:
            setattr(instance, field, validated_data.get(field))
        instance.save()
        return instance


class NewsInResidentialSerializer(ModelSerializer):

    class Meta:
        model = News
        exclude = ['residential_complex', 'body']


class ResidentialComplexListSerializer(ModelSerializer):
    flats_information = FlatSquarePriceField(source='*', read_only=True)

    class Meta:
        model = ResidentialComplex
        fields = ['id', 'photo', 'name', 'address', 'flats_information']


class ResidentialComplexSerializer(ModelSerializer):
    owner = AuthRegistrationSerializer(read_only=True)
    additions = AdditionInComplexSerializer(many=True, required=False)
    gallery_photos = PhotoSerializer(many=True, required=False)
    documents = DocumentDisplaySerializer(source='document_set', read_only=True, many=True)
    flats_information = FlatSquarePriceField(source='*', read_only=True)
    corps = CorpsInResidentialSerializer(source='corps_set', read_only=True, many=True)
    news = NewsInResidentialSerializer(source='news_set', read_only=True, many=True)

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

        if additions:
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

        if gallery:
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
                'additions': AdditionInComplexSerializer(instance=instance.additionincomplex_set.all(), many=True).data,
             }
        )
        return data


class FloorSerializer(ModelSerializer):
    name = CharField(read_only=True)
    residential_complex = ResidentialComplexDisplayField(read_only=True)

    class Meta:
        model = Floor
        fields = '__all__'


class FlatBuilderSerializer(ModelSerializer):
    gallery_photos = PhotoSerializer(source='gallery.photo_set', required=False, many=True)

    class Meta:
        model = Flat
        exclude = ['residential_complex', 'gallery']

    def create(self, validated_data):
        validated_data['residential_complex'] = self.context.get('residential_complex')
        instance = Flat.objects.create(
            gallery=Gallery.objects.create(),
            **validated_data
        )
        return instance

    def update(self, instance, validated_data):
        for field in validated_data:
            setattr(instance, field, validated_data.get(field))
        instance.save()
        return instance


class PhotoBase64Serializer(ModelSerializer):
    photo = Base64ImageField()

    class Meta:
        model = Photo
        exclude = ['gallery']


class ChessBoardFlatAnnouncementSerializer(ModelSerializer):
    gallery_photos = PhotoBase64Serializer(source='gallery.photo_set', required=False, many=True)

    class Meta:
        model = ChessBoardFlat
        exclude = ['flat', 'chessboard', 'gallery', 'accepted', 'creator']
