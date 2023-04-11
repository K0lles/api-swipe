from django.core.management.base import BaseCommand
from faker import Faker
from random import choice, randint

from flats.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        faker = Faker('uk_UA')
        users = User.objects.filter(role__role='builder')
        if users.exists() and not ResidentialComplex.objects.all().exists():
            for el in users:
                user = choice(users)
                users = users.all().exclude(email=user.email)
                rc = ResidentialComplex.objects.create(
                    owner=user,
                    name=faker.company(),
                    photo='init_scripts/residential_complex/1.jpg',
                    address=faker.address(),
                    map_code='<div></div>',
                    description=faker.catch_phrase(),
                    status=choice(['flats', 'cottage', 'many-floors', 'secondary-market']),
                    price_for_meter=randint(20, 65),
                    min_price=randint(20000, 190000),
                    house_type=choice(['cottage', 'many-floors', 'secondary-market']),
                    house_class=choice(['lux', 'elite', 'common']),
                    building_technology='bricks',
                    territory_type=choice(['closed', 'opened', 'closed-and-secured']),
                    sea_distance=randint(1, 800),
                    ceiling_altitude=randint(1, 4),
                    gas=True,
                    heating='centralized',
                    electricity=True,
                    sewage='centralized',
                    water_supply='centralized',
                    arrangement='justice',
                    payment=choice(['mortgage', 'parent-capital']),
                    purpose='living-building',
                    sum_in_contract='full',
                    gallery=Gallery.objects.create()
                )

                for i in range(1, 4):
                    Corps.objects.create(
                        name=f'Корпус {i}',
                        residential_complex=rc
                    )

                    Section.objects.create(
                        name=f'Секція {i}',
                        residential_complex=rc
                    )

                    Floor.objects.create(
                        name=f'Поверх {i}',
                        residential_complex=rc
                    )

                flat = Flat.objects.create(
                    residential_complex=rc,
                    scheme='init_scripts/flats/1.jpg',
                    floor=choice(rc.floor_set.all()),
                    section=choice(rc.section_set.all()),
                    corps=choice(rc.corps_set.all()),
                    gallery=Gallery.objects.create(),
                    district=faker.city_name(),
                    micro_district=faker.street_name(),
                    room_amount=randint(1, 6),
                    square=randint(40, 250),
                    price=randint(35000, 290000),
                    condition='living-condition'
                )

                chessboard, created = ChessBoard.objects.get_or_create(residential_complex=rc,
                                                                       corps=flat.corps,
                                                                       section=flat.section)

                ChessBoardFlat.objects.create(
                    residential_complex=rc,
                    flat=flat,
                    chessboard=chessboard,
                    gallery=Gallery.objects.create(),
                    address=faker.address(),
                    accepted=True,
                    purpose='apartments',
                    room_amount=randint(1, 6),
                    planning=choice(['studio-bathroom', 'studio']),
                    house_condition=choice(['repair-required', 'good']),
                    overall_square=randint(40, 260),
                    kitchen_square=randint(20, 45),
                    has_balcony=choice([True, False]),
                    heating_type=choice(['gas', 'centralized']),
                    payment_option='parent-capital',
                    agent_commission=randint(50, 800),
                    communication_method=choice(['phone-messages', 'phone', 'messages']),
                    description=faker.catch_phrase(),
                    price=randint(40000, 290000),
                    main_photo='init_scripts/chessboardflat/1.jpg',
                    creator=choice(User.objects.filter(role__role='user')),
                    called_off=False
                )

        if not PromotionType.objects.all().exists():
            PromotionType.objects.create(
                name='common',
                price=2.99,
                efficiency=3
            )

            PromotionType.objects.create(
                name='lux',
                price=5.99,
                efficiency=6
            )

            PromotionType.objects.create(
                name='elite',
                price=9.99,
                efficiency=10
            )
