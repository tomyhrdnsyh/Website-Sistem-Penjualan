from .models import *
from django import forms
from django.forms import ModelForm


class Penjualan(ModelForm):

    # tanggal jual
    tanggal_jual = forms.CharField(label='Tanggal jual', widget=forms.widgets.DateTimeInput(
        attrs={'placeholder': 'Tanggal Jual',
               'type': 'date',
               'class': 'form-control form-custom',
               'data-toggle': 'tooltip',
               'title': 'Masukan Tanggal Jual'}))

    class Meta:
        model = FakturPenjualan
        fields = ['tanggal_jual']


class FormDistributor(ModelForm):
    nama_distributor = forms.CharField(label='Nama Distributor', widget=forms.widgets.TextInput(
        attrs={'class': 'form-control form-custom',
               'placeholder': 'John Doe',
               'data-toggle': 'tooltip',
               'title': 'Nama Lengkap'}))
    no_telepon = forms.CharField(max_length=100, label='Nomor HP', widget=forms.TextInput(
        attrs={'class': 'form-control form-custom',
               'placeholder': '087788998887',
               'pattern': '[0-9]\d{8,16}'}))

    alamat_distributor = forms.CharField(max_length=254, label='Alamat', widget=forms.TextInput(
        attrs={'class': 'form-control form-custom',
               'placeholder': 'Greenwich Village',
               'data-toggle': 'tooltip',
               'title': 'Alamat Sekarang'}))

    class Meta:
        model = Distributor
        fields = ['nama_distributor', 'no_telepon', 'alamat_distributor']
