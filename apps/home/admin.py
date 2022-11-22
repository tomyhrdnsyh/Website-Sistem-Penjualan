# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import *

# Register your models here.
# admin.site.register(CustomUser)


class CustomUserAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            'Additional Info',
            {
                'fields': (
                    'no_hp_pengguna',
                    'nama_pengguna',
                )
            }
        )
    )
    list_display = ('id_pengguna', 'username', 'email', 'first_name', 'last_name', 'no_hp_pengguna', )


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ("nama_distributor", "no_telepon", "alamat_distributor")


@admin.register(Petugas)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ("nama_petugas", "distributor")


@admin.register(FakturPembelian)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("pengguna", "tanggal_pembelian", "tunai")


@admin.register(DetailFakturPembelian)
class PurchaseInvoiceDetailAdmin(admin.ModelAdmin):
    list_display = ("faktur_pembelian", "produk", "kuantitas")


@admin.register(Produk)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("nama_produk", "jenis_produk")


@admin.register(DetailProduk)
class ProductDetailAdmin(admin.ModelAdmin):
    list_display = ("produk", "stok", "tanggal_kadaluarsa", "harga_jual_satuan")


admin.site.register(JenisProduk)


@admin.register(FakturPenjualan)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("konsumen", "tanggal_jual")


@admin.register(DetailFakturPenjualan)
class SalesInvoiceDetailAdmin(admin.ModelAdmin):
    list_display = ("faktur_penjualan", "produk", "kuantitas")


@admin.register(Konsumen)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("nama_konsumen", "alamat_konsumen")

