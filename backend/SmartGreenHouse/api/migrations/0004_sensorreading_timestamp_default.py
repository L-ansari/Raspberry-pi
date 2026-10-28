from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [('api', '0003_plant_plantanalysis')]
    operations = [migrations.AlterField(
        model_name='sensorreading', name='timestamp',
        field=models.DateTimeField(default=timezone.now),
    )]
