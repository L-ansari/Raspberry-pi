import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('api', '0002_edgenode_owner'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='Plant', fields=[
            ('id', models.SlugField(primary_key=True, max_length=80, serialize=False)),
            ('name', models.CharField(max_length=100)),
            ('scientific_name', models.CharField(max_length=150)),
            ('aliases', models.JSONField(default=list, blank=True)),
            ('is_active', models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name='PlantAnalysis', fields=[
            ('id', models.CharField(primary_key=True, max_length=36, default=uuid.uuid4, editable=False, serialize=False)),
            ('range', models.CharField(max_length=3)),
            ('snapshot', models.JSONField()), ('result', models.JSONField()),
            ('model_name', models.CharField(max_length=150)),
            ('schema_version', models.PositiveSmallIntegerField(default=1)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE)),
            ('plant', models.ForeignKey(to='api.plant', on_delete=django.db.models.deletion.PROTECT)),
        ]),
    ]
