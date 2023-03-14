from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from users.models import User


class Gallery(models.Model):
    pass


class ResidentialComplex(models.Model):
    owner = models.OneToOneField(User, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    map_code = models.TextField()
    description = models.TextField()
    photo = models.ImageField(upload_to='residential_complex/photos/')

    class Status(models.TextChoices):
        # TODO: which statuses could have complex?
        flat = ('flats', 'Квартири')
        cottage = ('cottage', 'Котедж')
        many_floors = ('many-floors', 'Багатоповерхівка')
        secondary_market = ('secondary-market', 'Вторинний ринок')

    status = models.CharField(max_length=50, choices=Status.choices, default='flats')
    price_for_meter = models.FloatField(validators=[MinValueValidator(1.00)])
    min_price = models.FloatField(validators=[MinValueValidator(1.00)])

    class HouseType(models.TextChoices):
        cottage = ('cottage', 'Котедж')
        many_floors = ('many-floors', 'Багатоповерхівка')
        secondary_market = ('secondary-market', 'Вторинний ринок')

    house_type = models.CharField(max_length=50, choices=HouseType.choices)

    class HouseClass(models.TextChoices):
        lux = ('lux', 'Люкс')
        elite = ('elite', 'Елітний')
        common = ('common', 'Загальний')

    house_class = models.CharField(max_length=50, choices=HouseClass.choices)

    class BuildingTechnology(models.TextChoices):
        bricks = ('bricks', 'Цегляний')
        # TODO: are there many other types?

    building_technology = models.CharField(max_length=50, choices=BuildingTechnology.choices)

    class TerritoryType(models.TextChoices):
        closed = ('closed', 'Закрита')
        closed_and_secured = ('closed-and-secured', 'Закрита та охороняється')
        opened = ('opened', 'Відкрита')

    territory_type = models.CharField(max_length=50, choices=TerritoryType.choices)
    sea_distance = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True)
    ceiling_altitude = models.IntegerField(validators=[MinValueValidator(0)])
    gas = models.BooleanField(default=True)

    class HeatingChoice(models.TextChoices):
        central = ('centralized', 'Централізоване')
        # TODO: are there other types of heating?

    heating = models.CharField(max_length=50, choices=HeatingChoice.choices)
    electricity = models.BooleanField(default=True)

    class SewageChoice(models.TextChoices):
        central = ('centralized', 'Централізоване')
        # TODO: are there other types of sewage?

    sewage = models.CharField(max_length=50, choices=SewageChoice.choices)

    class WaterSupplyChoice(models.TextChoices):
        central = ('centralized', 'Централізоване')
        # TODO: are there other types of water supply?

    water_supply = models.CharField(max_length=50, choices=WaterSupplyChoice.choices)

    class ArrangementChoice(models.TextChoices):
        justice = ('justice', 'Юстиція')
        # TODO: are there other types of arrangements?

    arrangement = models.CharField(max_length=50, choices=ArrangementChoice.choices)

    class PaymentChoice(models.TextChoices):
        mortgage = ('mortgage', 'Іпотека')
        parent_capital = ('parent-capital', 'Материнський капітал')

    payment = models.CharField(max_length=50, choices=PaymentChoice.choices)

    class PurposeChoice(models.TextChoices):
        living_building = ('living-building', 'Житловий будинок')
        # TODO: the same

    purpose = models.CharField(max_length=50, choices=PurposeChoice.choices)

    class ContractSumChoice(models.TextChoices):
        full = ('full', 'Повна')
        part = ('part', 'Частинами')

    sum_in_contract = models.CharField(max_length=20, choices=ContractSumChoice.choices)
    gallery = models.OneToOneField(Gallery, on_delete=models.PROTECT)


class Document(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    document = models.FileField(upload_to='residential_complex/documents/')


class News(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
    header = models.CharField(max_length=200)
    body = models.TextField()
    date = models.DateTimeField(auto_now_add=True)


class Addition(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='additions/logos/')


class AdditionInComplex(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
    addition = models.ForeignKey(Addition, on_delete=models.SET_NULL, blank=True, null=True)
    turned_on = models.BooleanField(default=False)


class Section(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)


class Floor(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)


class Corps(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)


class Photo(models.Model):
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='photos/')
    created_at = models.DateTimeField(auto_now_add=True)
    sequence_number = models.IntegerField(validators=[MinValueValidator(0)])


class Flat(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.PROTECT)
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT)
    section = models.ForeignKey(Section, on_delete=models.PROTECT)
    corps = models.ForeignKey(Corps, on_delete=models.PROTECT)
    gallery = models.OneToOneField(Gallery, on_delete=models.PROTECT)
    district = models.CharField(max_length=200)
    micro_district = models.CharField(max_length=200)
    room_amount = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])
    scheme = models.ImageField(upload_to='flats/schemes/')
    square = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.IntegerField(validators=[MinValueValidator(1)])

    class ConditionType(models.TextChoices):
        draft = ('draft', 'Чорновик')
        living_condition = ('living-condition', 'Житлова')

    condition = models.CharField(max_length=20, choices=ConditionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)


class ChessBoard(models.Model):
    section = models.ForeignKey(Section, on_delete=models.PROTECT)
    corps = models.ForeignKey(Corps, on_delete=models.PROTECT)
    number = models.CharField(max_length=8)

    class Type(models.TextChoices):
        draft = ('draft', 'Чорновик')
        # TODO: the same

    chess_type = models.CharField(max_length=20, choices=Type.choices)
    created_at = models.DateField(auto_now_add=True)


class ChessBoardFlat(models.Model):
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.PROTECT)
    flat = models.ForeignKey(Flat, on_delete=models.PROTECT, blank=True, null=True)
    chessboard = models.ForeignKey(ChessBoard, on_delete=models.PROTECT, blank=True, null=True)
    gallery = models.OneToOneField(Gallery, on_delete=models.PROTECT)
    accepted = models.BooleanField(default=False)
    address = models.TextField()

    class FoundationDocumentType(models.TextChoices):
        property = ('property', 'Власність')

    class PurposeChoice(models.TextChoices):
        apartments = ('apartments', 'Квартири')
        # TODO: are these purposes equal to purposes in ResidentialComplex model?

    purpose = models.CharField(max_length=20, choices=PurposeChoice.choices)
    room_amount = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    class PlanningChoice(models.TextChoices):
        studio_bathroom = ('studio-bathroom', 'Студія і ванна')
        studio = ('studio', 'Студія')

    planning = models.CharField(max_length=30, choices=PlanningChoice.choices)

    class HouseCondition(models.TextChoices):
        repair_required = ('repair-required', 'Потрібен ремонт')
        good = ('good', 'Задовільний')
        # TODO: are these house conditions the same as in ResidentialComplex model?

    house_condition = models.CharField(max_length=30, choices=HouseCondition.choices)
    overall_square = models.FloatField(validators=[MinValueValidator(1)])
    kitchen_square = models.FloatField(validators=[MinValueValidator(1)])
    has_balcony = models.BooleanField(default=True)

    class HeatingType(models.TextChoices):
        gas = ('gas', 'Газ')
        centralized = ('centralized', 'Централізоване')
        # TODO: the same

    heating_type = models.CharField(max_length=20, choices=HeatingType.choices)

    class PaymentOption(models.TextChoices):
        parent_capital = ('parent-capital', 'Материнський капітал')
        # TODO: the same

    payment_option = models.CharField(max_length=20, choices=PaymentOption.choices)
    agent_commission = models.IntegerField(validators=[MinValueValidator(0)])

    class CommunicationMethod(models.TextChoices):
        phone_messages = ('phone-messages', 'Телефон і повідомлення')
        phone = ('phone', 'Тільки телефон')
        messages = ('messages', 'Тільки повідомлення')

    communication_method = models.CharField(max_length=40, choices=CommunicationMethod.choices)
    description = models.TextField()
    price = models.IntegerField(validators=[MinValueValidator(1)])
    main_photo = models.ImageField(upload_to='chessboard/main_photos/')
    creator = models.ForeignKey(User, on_delete=models.CASCADE)


class PromotionType(models.Model):
    name = models.CharField(max_length=200)
    price = models.FloatField(validators=[MinValueValidator(0.00)])
    efficiency = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])


class Promotion(models.Model):
    chessboard_flat = models.ForeignKey(ChessBoardFlat, on_delete=models.CASCADE)
    promotion_type = models.ForeignKey(PromotionType, on_delete=models.PROTECT)
    logo = models.ImageField(upload_to='promotions/')
    header = models.CharField(max_length=200, null=True)

    class ColorChoice(models.TextChoices):
        green = ('green', 'Зелений')
        red = ('red', 'Червоний')

    color = models.CharField(max_length=15, choices=ColorChoice.choices, blank=True, null=True)


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chessboard_flat = models.ForeignKey(ChessBoardFlat, on_delete=models.CASCADE)
    residential_complex = models.ForeignKey(ResidentialComplex, on_delete=models.CASCADE)
