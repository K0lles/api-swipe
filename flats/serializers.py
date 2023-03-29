from django.db import IntegrityError
from django.db.models import Max, Min
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField, BooleanField, ImageField, DateTimeField, DateField
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField, Serializer

from drf_extra_fields.fields import Base64ImageField

from .functions import update_gallery_photos
from .models import *
from users.serializers import AuthRegistrationSerializer


class DisplaySerializer(Serializer):
    model = None

    def to_internal_value(self, data):
        try:
            return self.model.objects.get(pk=data)
        except self.model.DoesNotExist:
            raise ValidationError({'detail': self.default_error_messages})

    def to_representation(self, value):
        return {
            'id': value.id,
            'name': value.name
        }
    
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ResidentialComplexDisplaySerializer(DisplaySerializer):
    model = ResidentialComplex

    def to_internal_value(self, data: int) -> ResidentialComplex:
        try:
            return ResidentialComplex.objects.get(pk=data)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})


class PhotoSerializer(ModelSerializer):
    id = IntegerField(required=False, write_only=False)
    photo = Base64ImageField(use_url=True)

    class Meta:
        model = Photo
        exclude = ['gallery', 'sequence_number']


class AdditionSerializer(ModelSerializer):
    logo = Base64ImageField(use_url=True)

    class Meta:
        model = Addition
        fields = '__all__'


class FlatSquarePriceSerializer(Serializer):

    def to_representation(self, value: ResidentialComplex):
        queryset = value.flat_set.all()
        flat_info = queryset \
            .values('square', 'price') \
            .aggregate(
                max_square=Max('square'),
                min_square=Min('square'),
                min_price=Min('price')
            )

        return {
            'maximal_square': flat_info.get('max_square', None),
            'minimal_square': flat_info.get('min_square', None),
            'minimal_price': flat_info.get('min_price', None)
        }


class CustomAdditionSerializer(ModelSerializer):

    class Meta:
        model = Addition
        fields = '__all__'

    def to_internal_value(self, data):
        try:
            instance = Addition.objects.get(pk=data)
        except Addition.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного додатку немає.')})
        return instance


class AdditionInComplexSerializer(ModelSerializer):
    id = IntegerField(required=False, write_only=False)
    addition = CustomAdditionSerializer(required=True)

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
    residential_complex = ResidentialComplexDisplaySerializer(read_only=True)

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
    residential_complex = ResidentialComplexDisplaySerializer(read_only=True)

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
    flats_information = FlatSquarePriceSerializer(source='*', read_only=True)

    class Meta:
        model = ResidentialComplex
        fields = ['id', 'photo', 'name', 'address', 'flats_information']


class ResidentialComplexSerializer(ModelSerializer):
    photo = Base64ImageField(use_url=True)
    owner = AuthRegistrationSerializer(read_only=True)
    gallery_photos = PhotoSerializer(many=True, required=False)
    flats_information = FlatSquarePriceSerializer(source='*', read_only=True)

    class Meta:
        model = ResidentialComplex
        exclude = ['gallery']

    def create(self, validated_data: dict):
        gallery = validated_data.pop('gallery_photos', None)
        try:
            residential_complex = ResidentialComplex.objects.create(
                owner=self.context.get('user'),
                gallery=Gallery.objects.create(),
                **validated_data
            )
        except IntegrityError:
            raise ValidationError({"detail": _("На вас уже зареєстровано ЖК.")})

        if gallery:
            for photo in gallery:
                Photo.objects.create(
                    photo=photo.get('photo'),
                    gallery=residential_complex.gallery,
                )

        return residential_complex

    def update(self, instance: ResidentialComplex, validated_data: dict):
        gallery = validated_data.pop('gallery_photos', None)

        for key in validated_data.keys():
            setattr(instance, key, validated_data.get(key))

        instance.save()

        update_gallery_photos(self.instance, gallery)

        return instance

    def to_representation(self, instance: ResidentialComplex):
        data = super().to_representation(instance=instance)
        data.update(
            {
                'gallery_photos': PhotoSerializer(instance=instance.gallery.photo_set.all(), many=True).data,
            }
        )
        return data


class FloorSerializer(ModelSerializer):
    name = CharField(read_only=True)
    residential_complex = ResidentialComplexDisplaySerializer(read_only=True)

    class Meta:
        model = Floor
        fields = '__all__'


class SectionFlatSerializer(ModelSerializer):

    class Meta:
        model = Section
        fields = ['id', 'name']

    def to_internal_value(self, data: int):
        try:
            return Section.objects.select_related('residential_complex').get(pk=data)
        except Section.DoesNotExist:
            raise ValidationError({'section': _('Вказана секція не існує.')})
        except TypeError:
            raise ValidationError({'section': _('Неправильно вказано секцію.')})


class FloorFlatSerializer(ModelSerializer):

    class Meta:
        model = Floor
        fields = ['id', 'name']

    def to_internal_value(self, data: int):
        try:
            return Floor.objects.select_related('residential_complex').get(pk=data)
        except Floor.DoesNotExist:
            raise ValidationError({'floor': _('Вказаний поверх не існує.')})


class CorpsFlatSerializer(ModelSerializer):

    class Meta:
        model = Corps
        fields = ['id', 'name']

    def to_internal_value(self, data: int):
        try:
            return Corps.objects.select_related('residential_complex').get(pk=data)
        except Corps.DoesNotExist:
            raise ValidationError({'corps': _('Вказаний корпус не існує.')})
        except TypeError:
            raise ValidationError({'corps': _('Неправильно вказано корпус.')})


class FlatListSerializer(ModelSerializer):
    corps = CorpsFlatSerializer()
    floor = FloorFlatSerializer()
    section = SectionFlatSerializer()
    residential_complex = ResidentialComplexDisplaySerializer()

    class Meta:
        model = Flat
        fields = ['corps', 'floor', 'section', 'scheme', 'residential_complex']

    def to_internal_value(self, data: int):
        try:
            flat = Flat.objects.select_related('residential_complex', 'section', 'corps').get(pk=data)
            return flat
        except Flat.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної квартири не існує.')})
        except TypeError:
            raise ValidationError({'detail': _('Неправильно вказано квартиру.')})


class FlatBuilderSerializer(ModelSerializer):
    residential_complex = ResidentialComplexDisplaySerializer()
    section = SectionFlatSerializer()
    floor = FloorFlatSerializer()
    corps = CorpsFlatSerializer()
    scheme = Base64ImageField(use_url=True)
    gallery_photos = PhotoSerializer(source='gallery.photo_set', required=False, many=True)

    class Meta:
        model = Flat
        exclude = ['gallery']

    def validate(self, attrs):
        if attrs.get('section', None) and attrs.get('floor', None) and attrs.get('corps', None):
            if attrs.get('section', None).residential_complex != attrs.get('floor').residential_complex \
                    != attrs.get('corps').residential_complex:
                raise ValidationError({'corps': _('Корпус, секція та поверх повинні бути із одного ЖК.'),
                                       'section': _('Корпус, секція та поверх повинні бути із одного ЖК.'),
                                       'floor': _('Корпус, секція та поверх повинні бути із одного ЖК.')})
        return super().validate(attrs)

    def create(self, validated_data):
        gallery = validated_data.pop('gallery', None)
        gallery_photos = gallery.get('photo_set', None) if gallery else None

        validated_data['residential_complex'] = self.context.get('residential_complex')
        instance = Flat.objects.create(
            gallery=Gallery.objects.create(),
            **validated_data
        )

        if gallery_photos:
            for index, item in enumerate(gallery_photos):
                Photo.objects.create(
                    gallery=instance.gallery,
                    photo=item.get('photo'),
                    sequence_number=index + 1
                )

        return instance

    def update(self, instance, validated_data):
        gallery = validated_data.pop('gallery', None)
        gallery_photos = gallery.get('photo_set', None) if gallery else None

        for field in validated_data:
            setattr(instance, field, validated_data.get(field))
        instance.save()

        update_gallery_photos(self.instance, gallery_photos, use_sequence=True)

        return instance

    def to_representation(self, instance: Flat):
        data = super().to_representation(instance)
        data.update(
            {
                'gallery_photos': PhotoSerializer(instance=instance.gallery.photo_set.all().order_by('sequence_number'), many=True).data
            }
        )
        return data


class PromotionTypeSerializer(ModelSerializer):

    class Meta:
        model = PromotionType
        fields = '__all__'


class ChessBoardListSerializer(ModelSerializer):
    """
    Serializer for displaying ChessBoard with bounded corps and section.
    """
    created_at = DateField(format='%d.%m.%Y')
    section = SectionFlatSerializer()
    corps = CorpsFlatSerializer()

    class Meta:
        model = ChessBoard
        fields = ['id', 'corps', 'section', 'created_at']


class FlatInChessFlatSerializer(ModelSerializer):
    """
    For short preview of flat inside ChessBoardFlat while revising
    separate ChessBoard
    """
    floor = FloorFlatSerializer()

    class Meta:
        model = Flat
        fields = ['id', 'floor', 'scheme']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['price_per_meter'] = instance.price / instance.square
        return data


class ChessFlatInChessBoardSerializer(ModelSerializer):
    """
    For display ChessBoardFlats inside certain ChessBoard on certain
    corps and section.
    """
    flat = FlatInChessFlatSerializer()

    class Meta:
        model = ChessBoardFlat
        fields = ['flat', 'kitchen_square', 'price']


class ChessBoardSerializer(ModelSerializer):
    section = SectionFlatSerializer()
    corps = CorpsFlatSerializer()
    flats = ChessFlatInChessBoardSerializer(source='chessboardflat_set', many=True)

    class Meta:
        model = ChessBoard
        fields = ['section', 'corps', 'flats']

    def validate(self, attrs):
        if not self.context.get('residential_complex', None):
            raise AttributeError(f'Residential Complex must be chosen while initializing {__class__} instance.')

        if attrs.get('corps', None).residential_complex != self.context.get('residential_complex') \
                != attrs.get('section', None).residential_complex:
            raise ValidationError({'corps': _('Корпус має належати тому саму ЖК, що і шахматка.'),
                                   'section': _('Секція має належати тому саму ЖК, що і шахматка.')})

        if ChessBoard.objects.filter(residential_complex=self.context.get('residential_complex'),
                                     corps=attrs.get('corps'),
                                     section=attrs.get('section')).exists():
            raise ValidationError({'corps': _('Шахматка із даним корпусом та секцією вже існує.'),
                                   'section': _('Шахматка із даним корпусом та секцією вже існує.')})

        return attrs

    def create(self, validated_data):
        instance = ChessBoard.objects.create(
            residential_complex=self.context.get('residential_complex'),
            **validated_data
        )

        return instance


class ChessBoardFlatAnnouncementListSerializer(ModelSerializer):
    residential_complex = ResidentialComplexDisplaySerializer()
    creator = AuthRegistrationSerializer()

    class Meta:
        model = ChessBoardFlat
        fields = ['residential_complex', 'creator', 'accepted', 'main_photo']


class ChessBoardFlatAnnouncementSerializer(ModelSerializer):
    """
    Serializer for creating announcements by users
    indicating RC, main photo etc.
    """
    main_photo = Base64ImageField(use_url=True)
    creator = AuthRegistrationSerializer(read_only=True)
    residential_complex = ResidentialComplexDisplaySerializer()
    accepted = BooleanField(read_only=True)
    gallery_photos = PhotoSerializer(required=False, many=True)

    class Meta:
        model = ChessBoardFlat
        exclude = ['flat', 'chessboard', 'gallery']

    def create(self, validated_data):
        gallery_photos = validated_data.pop('gallery_photos', None)
        instance = ChessBoardFlat.objects.create(
            gallery=Gallery.objects.create(),
            creator=self.context.get('user'),
            **validated_data
        )

        if gallery_photos:
            for index, dct in enumerate(gallery_photos):
                Photo.objects.create(
                    gallery=instance.gallery,
                    sequence_number=index + 1,
                    **dct
                )
        return instance

    def update(self, instance, validated_data):
        gallery_photos = validated_data.pop('gallery_photos', None)

        for field in validated_data:
            setattr(instance, field, validated_data.get(field))

        instance.save()

        update_gallery_photos(self.instance, gallery_photos, use_sequence=True)

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(
            {
                'gallery_photos': PhotoSerializer(instance=instance.gallery.photo_set.all().order_by('sequence_number'), many=True).data
            }
        )
        return data


class AnnouncementListSerializer(ModelSerializer):
    """
    Serializer for listing both accepted or unaccepted announcements of builder.
    """

    class Meta:
        model = ChessBoardFlat
        fields = ['id', 'main_photo', 'price', 'payment_option', 'house_condition']


class AnnouncementApproveSerializer(ModelSerializer):
    """
    Serializer for builder to accept and modify announcements create by
    users.
    Only update() method is user here, as announcement already exists
    and builder is approving it.
    """
    creator = AuthRegistrationSerializer(read_only=True)
    main_photo = Base64ImageField(use_url=True, required=False)
    flat = FlatListSerializer()
    gallery_photos = PhotoSerializer(required=False, many=True)
    residential_complex = ResidentialComplexDisplaySerializer()
    chessboard = ChessBoardSerializer(read_only=True)

    class Meta:
        model = ChessBoardFlat
        exclude = ['gallery']

    def validate(self, attrs):
        # checking whether flat is absent while 'accepted' set to True
        if attrs.get('accepted', None) and not attrs.get('flat', None):
            raise ValidationError({'flat': _('При підтвердженні об`яви має бути указана квартира.')})

        # checking whether flat's RC equals RC of self.instance
        if attrs.get('flat', None).residential_complex != self.instance.residential_complex:
            raise ValidationError({'detail': _('Квартира повинна належати вашому ЖК.')})

        # getting or creating chessboard, on which current announcement will be registered
        chessboard, created = ChessBoard.objects.get_or_create(residential_complex=self.instance.residential_complex,
                                                               corps=attrs.get('flat').corps,
                                                               section=attrs.get('flat').section)
        attrs['chessboard'] = chessboard

        return attrs

    def update(self, instance: ChessBoardFlat, validated_data):
        gallery_photos = validated_data.pop('gallery_photos', None)

        for field in validated_data:
            setattr(instance, field, validated_data.get(field))

        update_gallery_photos(instance, gallery_photos, use_sequence=True)

        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(
            {
                'gallery_photos': PhotoSerializer(instance=instance.gallery.photo_set.all().order_by('sequence_number'), many=True).data
            }
        )
        return data
