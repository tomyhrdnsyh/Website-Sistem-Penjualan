# Generated by Django 3.2.16 on 2023-01-07 09:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0025_delete_detailfakturpenjualan'),
    ]

    operations = [
        migrations.CreateModel(
            name='DetailFakturPenjualan',
            fields=[
                ('id_detail_faktur_penjualan', models.AutoField(primary_key=True, serialize=False)),
                ('kuantitas', models.CharField(blank=True, max_length=250, null=True)),
                ('faktur_penjualan', models.ForeignKey(db_column='no_faktur_penjualan', on_delete=django.db.models.deletion.CASCADE, to='home.fakturpenjualan')),
            ],
            options={
                'verbose_name_plural': 'detail faktur penjualan',
                'db_table': 'detail_faktur_penjualan',
            },
        ),
        migrations.CreateModel(
            name='Quantity',
            fields=[
                ('id_kuantitas', models.AutoField(primary_key=True, serialize=False)),
                ('kuantitas', models.IntegerField()),
                ('detail_faktur_penjualan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.detailfakturpenjualan')),
                ('produk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.produk')),
            ],
            options={
                'db_table': 'kuantitas_penjualan',
            },
        ),
        migrations.AddField(
            model_name='detailfakturpenjualan',
            name='produk',
            field=models.ManyToManyField(db_column='id_produk', through='home.Quantity', to='home.Produk'),
        ),
    ]
