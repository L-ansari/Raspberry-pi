from django.core.management.base import BaseCommand
from api.models import Plant

PLANTS = [
    ('tomato', 'Tomato', 'Solanum lycopersicum', []),
    ('cucumber', 'Cucumber', 'Cucumis sativus', []),
    ('sweet-pepper', 'Sweet pepper', 'Capsicum annuum', ['Bell pepper']),
    ('eggplant', 'Eggplant', 'Solanum melongena', ['Aubergine']),
    ('lettuce', 'Lettuce', 'Lactuca sativa', []),
    ('spinach', 'Spinach', 'Spinacia oleracea', []),
    ('kale', 'Kale', 'Brassica oleracea var. sabellica', []),
    ('cabbage', 'Cabbage', 'Brassica oleracea var. capitata', []),
    ('broccoli', 'Broccoli', 'Brassica oleracea var. italica', []),
    ('carrot', 'Carrot', 'Daucus carota subsp. sativus', []),
    ('radish', 'Radish', 'Raphanus sativus', []),
    ('strawberry', 'Strawberry', 'Fragaria x ananassa', []),
    ('basil', 'Basil', 'Ocimum basilicum', ['Sweet basil']),
    ('mint', 'Mint', 'Mentha spicata', ['Spearmint']),
    ('coriander', 'Coriander', 'Coriandrum sativum', ['Cilantro']),
    ('parsley', 'Parsley', 'Petroselinum crispum', []),
    ('rosemary', 'Rosemary', 'Salvia rosmarinus', []),
    ('thyme', 'Thyme', 'Thymus vulgaris', []),
    ('chives', 'Chives', 'Allium schoenoprasum', []),
    ('pea', 'Pea', 'Pisum sativum', ['Garden pea']),
]


class Command(BaseCommand):
    help = 'Create or update the 20 shared English-language plants without duplicates.'

    def handle(self, *args, **options):
        for plant_id, name, scientific_name, aliases in PLANTS:
            Plant.objects.update_or_create(pk=plant_id, defaults={
                'name': name, 'scientific_name': scientific_name,
                'aliases': aliases, 'is_active': True,
            })
        self.stdout.write(self.style.SUCCESS('Seeded 20 English-language plants.'))
