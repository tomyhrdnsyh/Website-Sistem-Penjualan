# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    first_name = None
    last_name = None
    email = None
    id_pengguna = models.AutoField(primary_key=True)
    nama_lengkap = models.CharField(max_length=100, null=True)
    no_hp_pengguna = models.CharField(max_length=20, null=True)

    class Meta:
        verbose_name = 'pengguna'
        verbose_name_plural = 'pengguna'
        db_table = 'pengguna'


class Distributor(models.Model):
    id_distributor = models.AutoField(primary_key=True)
    nama_distributor = models.CharField(max_length=100)
    no_telepon = models.CharField(max_length=20)
    alamat_distributor = models.CharField(max_length=255)

    def __str__(self):
        return self.nama_distributor

    class Meta:
        verbose_name_plural = 'distributor'
        db_table = 'distributor'


class Petugas(models.Model):
    id_petugas = models.AutoField(primary_key=True)
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE,
                                    db_column='id_distributor')
    nama_petugas = models.CharField(max_length=100)

    def __str__(self):
        return self.nama_petugas

    class Meta:
        verbose_name_plural = 'petugas'
        db_table = 'petugas'


class JenisProduk(models.Model):  # jenis produk
    id_jenis_produk = models.AutoField(primary_key=True)
    nama_jenis_produk = models.CharField(max_length=100)

    def __str__(self):
        return self.nama_jenis_produk

    class Meta:
        verbose_name_plural = 'jenis produk'
        db_table = 'jenis_produk'


class Produk(models.Model):
    id_produk = models.AutoField(primary_key=True)
    jenis_produk = models.ForeignKey(JenisProduk, on_delete=models.CASCADE,
                                     db_column='id_jenis_produk')
    nama_produk = models.CharField(max_length=100)

    def __str__(self):
        return self.nama_produk

    class Meta:
        verbose_name_plural = 'produk'
        db_table = 'produk'


class FakturPembelian(models.Model):  # faktur pembelian
    no_faktur_pembelian = models.AutoField(primary_key=True)
    pengguna = models.ForeignKey(CustomUser, null=True, on_delete=models.CASCADE,
                                 db_column='id_pengguna')
    petugas = models.ForeignKey(Petugas, null=True, on_delete=models.CASCADE,
                                db_column='id_petugas')
    tanggal_pembelian = models.DateField()
    tunai = models.FloatField()

    def __str__(self):
        return str(self.pengguna)

    class Meta:
        verbose_name_plural = 'faktur pembelian'
        db_table = 'faktur_pembelian'


class DetailFakturPembelian(models.Model):  # detail faktur pembelian
    id_detail_faktur_pembelian = models.AutoField(primary_key=True)
    faktur_pembelian = models.ForeignKey(FakturPembelian, on_delete=models.CASCADE,
                                         db_column='no_faktur_pembelian')
    produk = models.ForeignKey(Produk, on_delete=models.CASCADE,
                               db_column='id_produk')
    kuantitas = models.IntegerField()
    harga_satuan = models.FloatField()

    def __str__(self):
        return str(self.produk)

    class Meta:
        verbose_name_plural = 'detail faktur pembelian'
        db_table = 'detail_faktur_pembelian'


class DetailProduk(models.Model):  # detail produk
    id_detail_produk = models.AutoField(primary_key=True)
    produk = models.ForeignKey(Produk, on_delete=models.CASCADE,
                               db_column='id_produk')
    faktur_pembelian = models.ForeignKey(FakturPembelian, on_delete=models.SET_NULL,
                                         null=True, db_column='no_faktur_pembelian')
    stok = models.IntegerField()
    tanggal_kadaluarsa = models.DateField()
    harga_jual_satuan = models.FloatField()

    def __str__(self):
        return str(self.produk)

    class Meta:
        verbose_name_plural = 'detail produk'
        db_table = 'detail_produk'


class Konsumen(models.Model):
    id_konsumen = models.AutoField(primary_key=True)
    nama_konsumen = models.CharField(max_length=100)
    alamat_konsumen = models.CharField(max_length=255)

    def __str__(self):
        return self.nama_konsumen

    class Meta:
        verbose_name_plural = 'konsumen'
        db_table = 'konsumen'


class FakturPenjualan(models.Model):  # faktur penjualan
    no_faktur_penjualan = models.AutoField(primary_key=True)
    konsumen = models.ForeignKey(Konsumen, db_column='id_konsumen', on_delete=models.CASCADE)
    tanggal_jual = models.DateField()

    def __str__(self):
        return str(self.no_faktur_penjualan)

    class Meta:
        verbose_name_plural = 'faktur penjualan'
        db_table = 'faktur_penjualan'


class DetailFakturPenjualan(models.Model):  # detail faktur penjualan
    id_detail_faktur_penjualan = models.AutoField(primary_key=True)
    faktur_penjualan = models.ForeignKey(FakturPenjualan, on_delete=models.CASCADE,
                                         db_column='no_faktur_penjualan')
    produk = models.ManyToManyField(Produk, db_column='id_produk', through='Quantity')

    def __str__(self):
        return str(self.id_detail_faktur_penjualan)

    class Meta:
        verbose_name_plural = 'detail faktur penjualan'
        db_table = 'detail_faktur_penjualan'


class Quantity(models.Model):
    id_kuantitas = models.AutoField(primary_key=True)
    detail_faktur_penjualan = models.ForeignKey(DetailFakturPenjualan, on_delete=models.CASCADE)
    produk = models.ForeignKey(Produk, on_delete=models.CASCADE)
    kuantitas = models.IntegerField()

    def __str__(self):
        return str(self.kuantitas)

    class Meta:
        db_table = 'kuantitas_penjualan'
