# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import *



class CustomUserAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            'Informasi lain',
            {
                'fields': (
                    'no_hp_pengguna',
                    'nama_lengkap',
                )
            }
        )
    )
    list_display = ('id_pengguna', 'username', 'no_hp_pengguna')


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ("id_distributor", "nama_distributor", "no_telepon", "alamat_distributor")


@admin.register(Petugas)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ("id_petugas", "nama_petugas", "distributor")


@admin.register(FakturPembelian)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("no_faktur_pembelian", "pengguna", "tanggal_pembelian", "tunai")


@admin.register(DetailFakturPembelian)
class PurchaseInvoiceDetailAdmin(admin.ModelAdmin):
    list_display = ("id_detail_faktur_pembelian", "faktur_pembelian", "produk", "kuantitas")


@admin.register(Produk)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id_produk", "nama_produk", "jenis_produk")


@admin.register(DetailProduk)
class ProductDetailAdmin(admin.ModelAdmin):
    list_display = ("id_detail_produk", "produk", "stok", "tanggal_kadaluarsa", "harga_jual_satuan")


# admin.site.register(JenisProduk)
@admin.register(JenisProduk)
class JenisProduk(admin.ModelAdmin):
    list_display = ('id_jenis_produk', 'nama_jenis_produk')


@admin.register(FakturPenjualan)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("no_faktur_penjualan", "konsumen", "tanggal_jual")


@admin.register(DetailFakturPenjualan)
class SalesInvoiceDetailAdmin(admin.ModelAdmin):
    list_display = ("id_detail_faktur_penjualan", "faktur_penjualan")


@admin.register(Konsumen)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id_konsumen", "nama_konsumen", "alamat_konsumen")


@admin.register(Quantity)
class QuantityAdmin(admin.ModelAdmin):
    list_display = ("id_kuantitas", "detail_faktur_penjualan", "produk", "kuantitas")
