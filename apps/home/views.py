# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
from django import template
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from .models import *
from .form import Penjualan, FormDistributor
from datetime import datetime
from django.shortcuts import redirect
from django.contrib import messages
import pandas as pd
import re
import numpy as np


def normalisasi_harga_jual(nama_produk: str, jenis_produk: str):
    detail_produk = DetailProduk.objects. \
        filter(produk__nama_produk=nama_produk,
               produk__jenis_produk__nama_jenis_produk=jenis_produk). \
        values('id_detail_produk', 'produk__nama_produk', 'tanggal_kadaluarsa',
               'produk__detailfakturpembelian__harga_satuan')
    df = pd.DataFrame(detail_produk)
    df.tanggal_kadaluarsa = [item.year for item in df.tanggal_kadaluarsa]
    df_groupby = df.groupby(['produk__nama_produk', 'tanggal_kadaluarsa']).mean()
    dd_raw_detail_produk = defaultdict(lambda: defaultdict(float))
    for index, rows in df_groupby.iterrows():
        dd_raw_detail_produk[index[0]][index[1]] = rows.produk__detailfakturpembelian__harga_satuan

    dd_clean_detail_produk = defaultdict(lambda: defaultdict(list))
    for produk, tahun_harga in dd_raw_detail_produk.items():
        n, steps = len(tahun_harga), []
        selisih = [item - list(tahun_harga.keys())[0] for item in tahun_harga.keys()]

        for index, (tahun, harga_beli) in enumerate(tahun_harga.items()):
            # bobot = (selisih[index] / sum(selisih) / 10)
            try:
                bobot = (selisih[index] / sum(selisih) / 10)
            except ZeroDivisionError:
                bobot = 0
            hj = (harga_beli * bobot + harga_beli)  # rumus harga jual = hb × bobot + hb

            hjp = hj * 0.2 + hj  # rumus hjp = hj * margin + hj; margin = 0.2

            dd_clean_detail_produk[produk][tahun] = [harga_beli, hjp]
            steps.append(tahun)

    output = {}
    for key, value in dd_clean_detail_produk.items():
        for tahun, harga in value.items():
            for item in detail_produk:
                if key == item['produk__nama_produk'] and tahun == item['tanggal_kadaluarsa'].year:
                    output[item['id_detail_produk']] = harga[-1]
    return output


def update_harga_jual_to_database(nama_produk: str, jenis_produk: str):
    clean_harga = normalisasi_harga_jual(nama_produk, jenis_produk)
    for key, value in clean_harga.items():
        update_harga_jual = DetailProduk.objects.get(id_detail_produk=key)
        update_harga_jual.harga_jual_satuan = value
        update_harga_jual.save()


@login_required(login_url="/login/")
def index(request):
    # =================== chart penjualan =================
    # query database
    detail_faktur_penjualan = DetailFakturPenjualan.objects. \
        order_by('faktur_penjualan__tanggal_jual').values('id_detail_faktur_penjualan', 'kuantitas',
                                                          'faktur_penjualan__tanggal_jual',
                                                          'faktur_penjualan__konsumen__nama_konsumen')

    raw_penjualan = defaultdict(list)
    for item in detail_faktur_penjualan:
        raw_penjualan[item['faktur_penjualan__tanggal_jual']].append(item['kuantitas'])

    penjualan_data = [sum(item) for item in raw_penjualan.values()]
    penjualan_labels_line = [datetime.strftime(item, "%d-%m-%y") for item in raw_penjualan.keys()]

    raw_penjualan_pie = defaultdict(list)
    for item in detail_faktur_penjualan:
        raw_penjualan_pie[item['faktur_penjualan__konsumen__nama_konsumen']].append(item['kuantitas'])

    penjualan_data_pie = [sum(item) for item in raw_penjualan_pie.values()]
    penjualan_labels_pie = [item for item in raw_penjualan_pie.keys()]

    # =================== chart pembelian =================

    # query database
    purchase_invoice = FakturPembelian.objects.order_by('tanggal_pembelian').values('tanggal_pembelian',
                                                                                    'detailfakturpembelian__harga_satuan',
                                                                                    'detailfakturpembelian__kuantitas')

    raw_pembelian = defaultdict(list)
    for item in purchase_invoice:
        if item['detailfakturpembelian__harga_satuan'] is not None and item[
            'detailfakturpembelian__kuantitas'] is not None:
            raw_pembelian[item['tanggal_pembelian']].append(
                item['detailfakturpembelian__harga_satuan'] * item['detailfakturpembelian__kuantitas'])

    pembelian_data = [sum(item) for item in raw_pembelian.values()]
    pembelian_labels = [datetime.strftime(item, "%d-%m-%y") for item in raw_pembelian.keys()]

    # total pembelian dan penjualan
    total_pembelian = int(sum([item['kuantitas'] * item['harga_satuan'] for item in
                               DetailFakturPembelian.objects.values('kuantitas', 'harga_satuan')]))
    total_pembelian = f'{total_pembelian:,}'[:15]

    total_penjualan = FakturPenjualan.objects.values('detailfakturpenjualan__kuantitas',
                                                     'detailfakturpenjualan__produk__detailproduk__harga_jual_satuan')

    total_penjualan = int(sum([item['detailfakturpenjualan__kuantitas']
                               * item['detailfakturpenjualan__produk__detailproduk__harga_jual_satuan']
                               for item in total_penjualan
                               if item['detailfakturpenjualan__produk__detailproduk__harga_jual_satuan'] is not None and
                               item['detailfakturpenjualan__kuantitas'] is not None]))
    total_penjualan = f'{total_penjualan:,}'[:15]
    # mengirim ke frontend
    context = {'segment': 'index', 'penjualan_data': penjualan_data, 'penjualan_labels_line': penjualan_labels_line,
               'penjualan_labels_pie': penjualan_labels_pie, 'penjualan_data_pie': penjualan_data_pie,
               'pembelian_data': pembelian_data,
               'pembelian_labels': pembelian_labels, 'total_produk': len(Produk.objects.all()),
               'total_pembelian': total_pembelian, 'total_penjualan': total_penjualan,
               'total_distributor': len(Distributor.objects.all())}

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def pages(request):
    context = {}

    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    # try:

    load_template = request.path.split('/')[-1]

    # MENU ADMIN
    if load_template == 'admin':
        return HttpResponseRedirect(reverse('admin:index'))

    # ====== MENU PENJUALAN ======
    if load_template == 'penjualan.html' or load_template == 'pdf-penjualan.html':
        # form modal
        get_data_produk = Produk.objects.order_by('detailproduk__tanggal_kadaluarsa').values(
            'detailproduk__tanggal_kadaluarsa',
            'nama_produk', 'id_produk', 'detailproduk__stok',
            'detailproduk__harga_jual_satuan')

        # gunakan variabel normalisasi_penjualan untuk menentukan stok dan harga jual produk
        # normalisasi adalah menggabungan produk yang sama dalam satu key dictionary,
        # sehingga 1 produk memiliki value object (list)

        normalisasi_penjualan = defaultdict(list)
        for index, rows in pd.DataFrame(get_data_produk).iterrows():
            normalisasi_penjualan[rows.nama_produk].append({'kadaluwarsa': rows.detailproduk__tanggal_kadaluarsa,
                                                            'id_produk': rows.id_produk,
                                                            'stok': rows.detailproduk__stok,
                                                            'harga_beli': rows.detailproduk__harga_jual_satuan})

        konsumen_choice = [
            {'value': item['id_konsumen'], 'option': item['nama_konsumen'].title()}
            for item in Konsumen.objects.values('nama_konsumen', 'id_konsumen')]

        produk_choice = [{'value': value[0].get('id_produk'), 'option': key}
                         for key, value in normalisasi_penjualan.items()]

        context['konsumen_form'] = konsumen_choice
        context['produk_form'] = produk_choice
        # end form modal

        context['form_penjualan'] = Penjualan

        # Tabel penjualan
        sales = FakturPenjualan.objects. \
            order_by('-no_faktur_penjualan').values('no_faktur_penjualan', 'konsumen__nama_konsumen',
                                                    'konsumen__alamat_konsumen',
                                                    'detailfakturpenjualan__produk__nama_produk',
                                                    'tanggal_jual', 'detailfakturpenjualan__kuantitas',
                                                    'detailfakturpenjualan__produk__id_produk',
                                                    'detailfakturpenjualan__produk__detailproduk__harga_jual_satuan')
        df_sales = pd.DataFrame(sales)
        df_groupby_sales = df_sales.groupby(
            by=['no_faktur_penjualan', 'detailfakturpenjualan__produk__nama_produk',
                'detailfakturpenjualan__produk__id_produk']).mean()

        raw_sales = defaultdict(lambda: defaultdict(dict))
        for index, rows in df_groupby_sales.iterrows():
            raw_sales[index[0]][index[1]] = {'id_product': int(index[2]), 'average_price': int(rows.detailfakturpenjualan__produk__detailproduk__harga_jual_satuan)}

        clean_sales = [{'no_faktur_penjualan': key,
                        'detailfakturpenjualan__produk__nama_produk': ', '.join([item for item in value.keys()]),
                        'harga_jual': ', '.join([str(item.get('average_price')) for item in value.values()]),
                        'detailfakturpenjualan__produk__id_produk': '.'.join([str(item.get('id_product')) for item in value.values()])
                        } for key, value in raw_sales.items()]

        for clean_sale in clean_sales:
            for sale in sales:
                if clean_sale.get('no_faktur_penjualan') == sale['no_faktur_penjualan']:
                    clean_sale['konsumen__nama_konsumen'] = sale['konsumen__nama_konsumen']
                    clean_sale['konsumen__alamat_konsumen'] = sale['konsumen__alamat_konsumen']
                    clean_sale['tanggal_jual'] = sale['tanggal_jual']
                    clean_sale['detailfakturpenjualan__kuantitas'] = sale['detailfakturpenjualan__kuantitas']
                    # clean_sale['detailfakturpenjualan__produk__id_produk'] = sale['detailfakturpenjualan__produk__id_produk']

                    harga_jual = clean_sale['harga_jual'].split(', ')
                    kuantitas = sale['detailfakturpenjualan__kuantitas'].split(', ')
                    total = np.array([int(item) for item in harga_jual]) * np.array([int(item) for item in kuantitas])

                    clean_sale['total'] = sum(total)

        context['penjualan'] = clean_sales
        # End tabel penjualan
        if request.POST:

            if 'update' in request.POST:
                id_global = re.findall(r'\d+', request.POST.get('id'))
                raw_check = check_stock_produk(normalisasi_penjualan=normalisasi_penjualan, req=request)
                if isinstance(raw_check, dict):
                    penjualan = FakturPenjualan.objects.get(no_faktur_penjualan=id_global[0])
                    penjualan.konsumen = Konsumen.objects.get(id_konsumen=request.POST.get('id_konsumen'))
                    penjualan.tanggal_jual = request.POST.get('tanggal_jual')
                    penjualan.save()
                else:
                    return raw_check

                # cek apakah id penjualan ada atau tidak, jika tidak create detail penjualan baru
                try:
                    detail_penjualan = DetailFakturPenjualan.objects.get(
                        faktur_penjualan=id_global[0])
                    detail_penjualan.kuantitas = request.POST.get('kuantitas')
                    detail_penjualan.produk = Produk.objects.get(id_produk=request.POST.get('id_produk'))
                    detail_penjualan.save()
                except:
                    detail_penjualan = DetailFakturPenjualan.objects.create(
                        faktur_penjualan=FakturPenjualan.objects.get(
                            no_faktur_penjualan=id_global[0]),
                        produk=Produk.objects.get(id_produk=request.POST.get('id_produk')),
                        kuantitas=request.POST.get('kuantitas'))

                if request.POST.get('kuantitas_sebelum') != 'Kosong':
                    update_stok = DetailProduk.objects.get(produk=detail_penjualan.produk.id_produk)
                    update_stok.stok = update_stok.stok + (
                            int(request.POST.get('kuantitas_sebelum')) - int(request.POST.get('kuantitas')))
                    update_stok.save()
                else:
                    add_data_penjualan(normalisasi_penjualan=normalisasi_penjualan,
                                       req=request, save_to_database=False)

            elif 'delete' in request.POST:
                id_global = re.findall(r'\d+', request.POST.get('id'))
                penjualan = FakturPenjualan.objects.get(no_faktur_penjualan=id_global[0])

                detail_penjualan = DetailFakturPenjualan.objects.get(faktur_penjualan=penjualan.no_faktur_penjualan)

                for index, item in enumerate(detail_penjualan.produk.all()):
                    update_stok = DetailProduk.objects.get(produk=item)
                    update_stok.stok = update_stok.stok + int(request.POST.get('kuantitas').split(', ')[index])
                    update_stok.save()

                penjualan.delete()

            else:
                # cek pada variabel normalisasi
                add_data_penjualan(normalisasi_penjualan=normalisasi_penjualan, req=request)

            return redirect('/penjualan.html')
    # ====== END MENU PENJUALAN ======

    # ====== MENU PEMBELIAN ======
    if load_template == 'pembelian.html' or load_template == 'pdf-pembelian.html':
        # form add data
        nama_distributor = [{'value': item['id_distributor'], 'option': item['nama_distributor']} for item in
                            Distributor.objects.values('id_distributor', 'nama_distributor')]
        jenis_produk = [{'value': item['id_jenis_produk'], 'option': item['nama_jenis_produk']} for item in
                        JenisProduk.objects.values('id_jenis_produk', 'nama_jenis_produk')]

        context['nama_distributor'] = nama_distributor
        context['jenis_produk'] = jenis_produk
        # end form add data

        # data table
        table_pembelian = FakturPembelian.objects.order_by('-no_faktur_pembelian').values(
            'no_faktur_pembelian', 'petugas__distributor__nama_distributor',
            'detailfakturpembelian__id_detail_faktur_pembelian',
            'tanggal_pembelian', 'detailfakturpembelian__produk__nama_produk',
            'detailfakturpembelian__kuantitas', 'detailfakturpembelian__harga_satuan',
            'detailfakturpembelian__produk__jenis_produk__nama_jenis_produk',
            'detailfakturpembelian__produk__detailproduk__tanggal_kadaluarsa',
            'detailfakturpembelian__produk__id_produk'
        )

        # Replace None value to Kosong
        for item in table_pembelian:
            for key, value in item.items():
                if value is None:
                    item[key] = 'Kosong'
                if isinstance(value, float):
                    item[key] = int(value)

        modal_edit_jenis_produk = [{'id_produk': item['detailfakturpembelian__produk__id_produk'],
                                    'kadaluarsa': str(
                                        item['detailfakturpembelian__produk__detailproduk__tanggal_kadaluarsa']),
                                    'jenis_produk': item[
                                        'detailfakturpembelian__produk__jenis_produk__nama_jenis_produk']}
                                   for item in table_pembelian]
        context['modal_edit_jenis_produk'] = modal_edit_jenis_produk

        for item in table_pembelian:
            if item.get('detailfakturpembelian__kuantitas') != 'Kosong' \
                    and item['detailfakturpembelian__harga_satuan'] != 'Kosong':
                item['total'] = item['detailfakturpembelian__kuantitas'] * item[
                    'detailfakturpembelian__harga_satuan']
            else:
                item['total'] = 'Kosong'

        context['table_pembelian'] = table_pembelian
        # end data table

        if request.POST:
            if 'delete' in request.POST:
                delete_pembelian = FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('id'))
                delete_pembelian.delete()

            elif 'update' in request.POST:

                id_global = re.findall(r'\d+', request.POST.get('id'))

                update_pemblian = FakturPembelian.objects.get(no_faktur_pembelian=id_global[0])
                update_pemblian.tanggal_pembelian = request.POST.get('tanggal_pembelian')
                update_pemblian.petugas = Petugas.objects.get(
                    distributor=Distributor.objects.get(id_distributor=request.POST.get('nama_distributor')))
                update_pemblian.save()

                if len(id_global) < 3:  # cek apakah id detail faktur pembelian dan produk == KOSONG
                    add_faktur_pembelian_detail_product(request, update_pemblian)
                else:
                    update_detail_pembelian = DetailFakturPembelian.objects.get(id_detail_faktur_pembelian=id_global[1])
                    update_detail_pembelian.harga_satuan = request.POST.get('harga_satuan')
                    update_detail_pembelian.kuantitas = request.POST.get('kuantitas')
                    update_detail_pembelian.save()

                    update_produk = Produk.objects.get(id_produk=id_global[2])
                    update_produk.nama_produk = request.POST.get('nama_produk')
                    update_produk.jenis_produk = JenisProduk.objects.get(
                        id_jenis_produk=request.POST.get('nama_jenis_produk'))
                    update_produk.save()

                    update_detail_produk = DetailProduk.objects.get(produk=update_produk.id_produk)
                    update_detail_produk.tanggal_kadaluarsa = request.POST.get('tanggal_kadaluarsa')
                    update_detail_produk.save()

                jenis_produk = JenisProduk.objects.get(id_jenis_produk=request.POST.get('nama_jenis_produk'))
                update_harga_jual_to_database(request.POST.get('nama_produk'), jenis_produk.nama_jenis_produk)

            else:
                insert_faktur_pembelian = FakturPembelian.objects.create(
                    tanggal_pembelian=request.POST.get('tanggal_pembelian'),
                    tunai=float(request.POST.get('harga_satuan')) * float(request.POST.get('kuantitas')),
                    pengguna=request.user,
                    petugas=Petugas.objects.get(
                        distributor=Distributor.objects.get(id_distributor=request.POST.get('nama_distributor'))),
                )

                # function add detail faktur pembelian, detail produk etc
                add_faktur_pembelian_detail_product(request, insert_faktur_pembelian)

                nama_jenis_produk = JenisProduk.objects.get(id_jenis_produk=request.POST.get('nama_jenis_produk'))
                update_harga_jual_to_database(request.POST.get('nama_produk'), nama_jenis_produk.nama_jenis_produk)
            return redirect('/pembelian.html')

    # ====== END MENU PEMBELIAN ======

    # ====== MENU PRODUK ======

    if load_template == 'product.html' or load_template == 'pdf-product.html':
        # form add produk
        no_faktur_pembelian = FakturPembelian.objects.values('no_faktur_pembelian')
        jenis_produk = JenisProduk.objects.values('nama_jenis_produk')

        context['no_faktur_pembelian'] = no_faktur_pembelian
        context['jenis_produk'] = jenis_produk
        # end form add produk

        # ===== table produk =====
        produk = Produk.objects.order_by('-id_produk').values(
            'id_produk', 'nama_produk', 'detailfakturpembelian__harga_satuan',
            'detailproduk__stok', 'jenis_produk__nama_jenis_produk', 'detailproduk__harga_jual_satuan',
            'detailproduk__tanggal_kadaluarsa', 'detailproduk__faktur_pembelian__no_faktur_pembelian'
        )
        # ----- replace None to kosong and change price type to int -----
        for item in produk:
            for key, value in item.items():
                if key in ['detailfakturpembelian__harga_satuan', 'detailproduk__harga_jual_satuan']:
                    if isinstance(value, float):
                        item[key] = int(value)

                if value is None:
                    item[key] = 'Kosong'
        # ----- end replace -----
        context['produk'] = produk
        # ===== end tabel produk =====

        if request.POST:

            if 'delete' in request.POST:
                id_global = re.findall(r'\d+', request.POST.get('id'))
                delete_produk = Produk.objects.get(id_produk=id_global[0])
                delete_produk.delete()

            elif 'update' in request.POST:
                id_global = re.findall(r'\d+', request.POST.get('id'))
                produk = Produk.objects.get(id_produk=id_global[0])
                produk.nama_produk = request.POST.get('nama_produk')
                produk.jenis_produk = JenisProduk.objects.get(nama_jenis_produk=request.POST.get('jenis_produk'))
                produk.save()

                # cek apakah detail faktur pembelian sudah ada
                try:
                    detail_faktur_pembelian = DetailFakturPembelian.objects.get(produk=produk.id_produk)
                    detail_faktur_pembelian.faktur_pembelian = FakturPembelian.objects.get(
                        no_faktur_pembelian=request.POST.get('no_faktur_pembelian'))
                    detail_faktur_pembelian.kuantitas = request.POST.get('kuantitas')
                    detail_faktur_pembelian.harga_satuan = request.POST.get('harga_satuan')
                    detail_faktur_pembelian.save()

                except:
                    DetailFakturPembelian.objects.create(
                        faktur_pembelian=FakturPembelian.objects.get(
                            no_faktur_pembelian=request.POST.get('no_faktur_pembelian')),
                        produk=Produk.objects.get(id_produk=produk.id_produk),
                        kuantitas=request.POST.get('kuantitas'),
                        harga_satuan=request.POST.get('harga_satuan')
                    )

                # cek apakah detail produk sudah ada
                try:
                    detail_produk = DetailProduk.objects.get(produk=produk.id_produk)
                    detail_produk.faktur_pembelian = FakturPembelian.objects.get(
                        no_faktur_pembelian=request.POST.get('no_faktur_pembelian'))
                    detail_produk.stok = request.POST.get('kuantitas')
                    detail_produk.tanggal_kadaluarsa = request.POST.get('tanggal_kadaluarsa')
                    detail_produk.harga_jual_satuan = float(request.POST.get('harga_satuan')) * 0.2 + float(
                        request.POST.get('harga_satuan'))
                    detail_produk.save()

                except:
                    DetailProduk.objects.create(
                        faktur_pembelian=FakturPembelian.objects.get(
                            no_faktur_pembelian=request.POST.get('no_faktur_pembelian')),
                        produk=Produk.objects.get(id_produk=produk.id_produk),
                        stok=request.POST.get('kuantitas'),
                        tanggal_kadaluarsa=request.POST.get('tanggal_kadaluarsa'),
                        harga_jual_satuan=float(request.POST.get('harga_satuan')) * 0.2 + float(
                            request.POST.get('harga_satuan'))
                    )
                update_harga_jual_to_database(request.POST.get('nama_produk'), request.POST.get('jenis_produk'))
            else:
                insert_produk = Produk.objects. \
                    create(nama_produk=request.POST.get('nama_produk'),
                           jenis_produk=JenisProduk.objects.get(nama_jenis_produk=request.POST.get('jenis_produk')))

                DetailFakturPembelian.objects.create(
                    faktur_pembelian=FakturPembelian.objects.get(
                        no_faktur_pembelian=request.POST.get('no_faktur_pembelian')),
                    produk=Produk.objects.get(id_produk=insert_produk.id_produk),
                    kuantitas=request.POST.get('kuantitas'),
                    harga_satuan=request.POST.get('harga_satuan')
                )

                DetailProduk.objects.create(
                    faktur_pembelian=FakturPembelian.objects.get(
                        no_faktur_pembelian=request.POST.get('no_faktur_pembelian')),
                    produk=Produk.objects.get(id_produk=insert_produk.id_produk),
                    stok=request.POST.get('kuantitas'),
                    tanggal_kadaluarsa=request.POST.get('tanggal_kadaluarsa'),
                    harga_jual_satuan=float(request.POST.get('harga_satuan')) * 0.2 + float(
                        request.POST.get('harga_satuan'))
                )

                update_harga_jual_to_database(request.POST.get('nama_produk'), request.POST.get('jenis_produk'))

            return redirect('/product.html')

    # ====== END MENU PRODUK ======

    # ====== MENU DISTRIBUTOR ======
    if load_template == 'distributor.html' or load_template == 'pdf-distributor.html':

        context['form_distributor'] = FormDistributor

        distributor = Distributor.objects.order_by('id_distributor').values(
            'id_distributor', 'nama_distributor', 'no_telepon', 'alamat_distributor'
        )
        context['distributor'] = distributor

        if request.POST:
            if 'delete' in request.POST:
                delete_distributor = Distributor.objects.get(id_distributor=request.POST.get('id'))
                delete_distributor.delete()

            elif 'update' in request.POST:
                update_distributor = Distributor.objects.get(id_distributor=request.POST.get('id'))
                update_distributor.nama_distributor = request.POST.get('nama_distributor')
                update_distributor.no_telepon = request.POST.get('no_telepon')
                update_distributor.alamat_distributor = request.POST.get('alamat_distributor')
                update_distributor.save()

            else:
                to_database = FormDistributor(request.POST)
                if to_database.is_valid():
                    to_database.save()
                    # save new petugas
                    petugas = Petugas(
                        distributor=to_database.instance,
                        nama_petugas=request.POST.get('nama_petugas')
                    )
                    petugas.save()

            return redirect('/distributor.html')

    # ====== END MENU DISTRIBUTOR ======

    context['segment'] = load_template
    html_template = loader.get_template('home/' + load_template)
    return HttpResponse(html_template.render(context, request))

    # except template.TemplateDoesNotExist:
    #
    #     html_template = loader.get_template('home/page-404.html')
    #     return HttpResponse(html_template.render(context, request))
    #
    # except:
    #     html_template = loader.get_template('home/page-500.html')
    #     return HttpResponse(html_template.render(context, request))


def check_stock_produk(normalisasi_penjualan, req):

    raw_kuantitas = [int(kuantitas) for kuantitas in req.POST.getlist('kuantitas')]  # list

    # mencari nama produk pada normalisasi penjualan
    nama_produk_kuantitas = defaultdict(list)
    for key, value in normalisasi_penjualan.items():
        for item in value:
            for index, id_produk in enumerate(req.POST.getlist('id_produk')):
                if id_produk == str(item.get('id_produk')):
                    nama_produk_kuantitas[key].append(raw_kuantitas[index])

    nama_produk = list(nama_produk_kuantitas.keys())
    kebutuhan_costumer = [sum(item) for item in nama_produk_kuantitas.values()]
    produk_yang_dipilih = [normalisasi_penjualan[nama] for nama in nama_produk]  # list
    total_stok = [sum([item['stok'] for item in produk]) for produk in produk_yang_dipilih]  # list

    # jika stok kurang dari kebutuhan costumer maka return pesan error dan data tidak disimpan
    for index, kebutuhan in enumerate(kebutuhan_costumer):
        if total_stok[index] < kebutuhan:
            messages.error(req,
                           f'Tambah penjualan gagal... Stok tidak mencukupi untuk produk yang anda pilih.'
                           f'Sisa stok {nama_produk[index]} : {total_stok[index]}')
            return redirect('/penjualan.html')
    return {'produk_yang_dipilih': produk_yang_dipilih, 'kebutuhan_costumer': kebutuhan_costumer}


def add_data_penjualan(normalisasi_penjualan, req, save_to_database=True):
    raw_check = check_stock_produk(normalisasi_penjualan, req)

    if isinstance(raw_check, dict):
        produk_yang_dipilih = raw_check['produk_yang_dipilih']
        kebutuhan_costumer = raw_check['kebutuhan_costumer']
    else:
        return raw_check

    # baru nyampe sini ya update nya
    penjualan__id_produk = []
    for index, jml_produk in enumerate(produk_yang_dipilih):
        temporary_stock = jml_produk[0].get('stok')
        for item in jml_produk:
            if kebutuhan_costumer[index] < temporary_stock:
                penjualan__id_produk.append(item.get('id_produk'))
                break
            else:
                penjualan__id_produk.append(item.get('id_produk'))
            temporary_stock += item.get('stok')

    to_database = Penjualan(req.POST)
    if to_database.is_valid():
        if save_to_database is True:
            to_database.instance.konsumen = Konsumen.objects.get(
                id_konsumen=req.POST.get('id_konsumen'))
            to_database.save()

            insert_to_detail_penjualan = DetailFakturPenjualan(
                faktur_penjualan=FakturPenjualan.objects.get(
                    no_faktur_penjualan=to_database.instance.no_faktur_penjualan),
                kuantitas=', '.join(str(item) for item in kebutuhan_costumer))
            insert_to_detail_penjualan.save()
            # save to ManyToManyField
            for item in penjualan__id_produk:
                produk = Produk.objects.get(id_produk=item)
                insert_to_detail_penjualan.produk.add(produk)
        return None
        # update stok produk berdasarkan kuantitas dari customer, diurutkan base on expired
        loop = True
        index = 0
        while loop:

            if int(produk_yang_dipilih[index].get('stok')) - kebutuhan_costumer <= 0:
                update_stok = DetailProduk.objects.get(produk=produk_yang_dipilih[index].get('id_produk'))
                update_stok.stok = 0
                kebutuhan_costumer = kebutuhan_costumer - produk_yang_dipilih[index].get('stok')
                update_stok.save()
            else:
                update_stok = DetailProduk.objects.get(produk=produk_yang_dipilih[index].get('id_produk'))
                update_stok.stok = update_stok.stok - kebutuhan_costumer
                kebutuhan_costumer = kebutuhan_costumer - produk_yang_dipilih[index].get('stok')
                update_stok.save()
            if kebutuhan_costumer <= 0:
                loop = False

            index += 1


def add_faktur_pembelian_detail_product(req, insert_faktur_pembelian):
    insert_produk = Produk.objects. \
        create(nama_produk=req.POST.get('nama_produk'),
               jenis_produk=JenisProduk.objects.get(
                   id_jenis_produk=req.POST.get('nama_jenis_produk')))

    DetailFakturPembelian.objects.create(
        faktur_pembelian=FakturPembelian.objects.get(
            no_faktur_pembelian=insert_faktur_pembelian.no_faktur_pembelian),
        produk=Produk.objects.get(id_produk=insert_produk.id_produk),
        kuantitas=req.POST.get('kuantitas'),
        harga_satuan=req.POST.get('harga_satuan')
    )

    DetailProduk.objects.create(
        faktur_pembelian=FakturPembelian.objects.get(
            no_faktur_pembelian=insert_faktur_pembelian.no_faktur_pembelian),
        produk=Produk.objects.get(id_produk=insert_produk.id_produk),
        stok=req.POST.get('kuantitas'),
        tanggal_kadaluarsa=req.POST.get('tanggal_kadaluarsa'),
        harga_jual_satuan=float(req.POST.get('harga_satuan')) * 0.2 + float(
            req.POST.get('harga_satuan'))
    )
