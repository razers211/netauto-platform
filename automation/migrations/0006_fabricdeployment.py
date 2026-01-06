# Generated migration for FabricDeployment model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('automation', '0005_alter_networktask_task_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='FabricDeployment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fabric_name', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('building', 'Building'), ('active', 'Active'), ('updating', 'Updating'), ('decommissioned', 'Decommissioned')], default='building', max_length=20)),
                ('underlay_ip_range', models.CharField(default='10.0.0.0/30', max_length=50)),
                ('as_number', models.IntegerField(default=65000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('spine_devices', models.JSONField(default=list, help_text='List of spine device IDs and configs')),
                ('leaf_devices', models.JSONField(default=list, help_text='List of leaf device IDs and configs')),
                ('border_leaf_devices', models.JSONField(default=list, help_text='List of border leaf device IDs and configs')),
                ('tenant_networks', models.JSONField(default=list, help_text='Tenant networks deployed in this fabric')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fabric_deployments', to='auth.user')),
            ],
            options={
                'verbose_name': 'Fabric Deployment',
                'verbose_name_plural': 'Fabric Deployments',
            },
        ),
    ]
