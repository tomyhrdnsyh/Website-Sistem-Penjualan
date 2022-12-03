from rest_framework import serializers
from apps.home.models import FakturPembelian, JenisProduk, Produk


class ItemSerializerPembelian(serializers.ModelSerializer):
    class Meta:
        model = FakturPembelian
        fields = ['no_faktur_pembelian']


class ItemSerializerJenisProduk(serializers.ModelSerializer):
    class Meta:
        model = JenisProduk
        fields = ['nama_jenis_produk']


class ItemSerializerAddProduk(serializers.ModelSerializer):
    class Meta:
        model = Produk
        fields = '__all__'
