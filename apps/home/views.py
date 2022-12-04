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
import pandas as pd


def normalisasi_harga_jual(nama_produk: str, jenis_produk: str):
    detail_produk = DetailProduk.objects.\
        filter(produk__nama_produk=nama_produk,
               produk__jenis_produk__nama_jenis_produk=jenis_produk).\
        values('id_detail_produk', 'produk__nama_produk', 'tanggal_kadaluarsa', 'produk__detailfakturpembelian__harga_satuan')
    df = pd.DataFrame(detail_produk)
    df.tanggal_kadaluarsa = [item.year for item in df.tanggal_kadaluarsa]
    df_groupby = df.groupby(['produk__nama_produk', 'tanggal_kadaluarsa']).mean()
    dd_raw_detail_produk = defaultdict(lambda: defaultdict(float))
    for index, rows in df_groupby.iterrows():
        dd_raw_detail_produk[index[0]][index[1]] = rows.produk__detailfakturpembelian__harga_satuan

    dd_clean_detail_produk = defaultdict(lambda: defaultdict(list))
    for produk, tahun_harga in dd_raw_detail_produk.items():
        n, steps = len(tahun_harga), []
        for tahun, harga_beli in tahun_harga.items():
            step = 0 if not steps else tahun - steps[-1]
            hj = (harga_beli * (step * 0.1 / n) + harga_beli)  # rumus harga jual = hb × bobot + hb
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
    purchase_invoice = FakturPembelian.objects.order_by('tanggal_pembelian').values('tanggal_pembelian', 'detailfakturpembelian__harga_satuan', 'detailfakturpembelian__kuantitas')

    raw_pembelian = defaultdict(list)
    for item in purchase_invoice:
        raw_pembelian[item['tanggal_pembelian']].append(item['detailfakturpembelian__harga_satuan'] * item['detailfakturpembelian__kuantitas'])

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
                               for item in total_penjualan]))
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
        konsumen_choice = [{'value': item['id_konsumen'], 'option': item['nama_konsumen'].title()}
                           for item in Konsumen.objects.values('nama_konsumen', 'id_konsumen')]
        produk_choice = [{'value': item['id_produk'], 'option': item['nama_produk'].title()}
                         for item in Produk.objects.values('nama_produk', 'id_produk')]

        context['konsumen_form'] = konsumen_choice
        context['produk_form'] = produk_choice
        # end form modal

        context['form_penjualan'] = Penjualan

        # Tabel penjualan
        sales = FakturPenjualan.objects. \
            order_by('no_faktur_penjualan').values('no_faktur_penjualan', 'konsumen__nama_konsumen',
                                                   'konsumen__alamat_konsumen',
                                                   'detailfakturpenjualan__produk__nama_produk',
                                                   'tanggal_jual', 'detailfakturpenjualan__kuantitas',
                                                   'detailfakturpenjualan__produk__detailproduk__harga_jual_satuan')

        for item in sales:
            if item.get('detailfakturpenjualan__kuantitas'):
                item['total'] = item['detailfakturpenjualan__kuantitas'] * item[
                    'detailfakturpenjualan__produk__detailproduk__harga_jual_satuan']
            else:
                item['total'] = None

        context['penjualan'] = sales
        # End tabel penjualan
        if request.POST:
            if 'update' in request.POST:
                penjualan = FakturPenjualan.objects.get(no_faktur_penjualan=request.POST.get('id'))
                penjualan.konsumen = Konsumen.objects.get(id_konsumen=request.POST.get('konsumen'))
                penjualan.tanggal_jual = request.POST.get('tanggal_jual')
                penjualan.save()

                # cek apakah id penjualan ada atau tidak, jika tidak create detail penjualan baru
                try:
                    detail_penjualan = DetailFakturPenjualan.objects.get(
                        faktur_penjualan=penjualan.no_faktur_penjualan)
                    detail_penjualan.kuantitas = request.POST.get('kuantitas')
                    detail_penjualan.produk = Produk.objects.get(id_produk=request.POST.get('produk'))
                    detail_penjualan.save()
                except:
                    detail_penjualan = DetailFakturPenjualan.objects.create(
                        faktur_penjualan=FakturPenjualan.objects.get(
                            no_faktur_penjualan=penjualan.no_faktur_penjualan),
                        produk=Produk.objects.get(id_produk=request.POST.get('produk')),
                        kuantitas=request.POST.get('kuantitas'))

                update_stok = DetailProduk.objects.get(produk=detail_penjualan.produk.id_produk)
                update_stok.stok = update_stok.stok + (
                            int(request.POST.get('harga_sebelum')) - int(request.POST.get('kuantitas')))
                update_stok.save()

            elif 'delete' in request.POST:
                penjualan = FakturPenjualan.objects.get(no_faktur_penjualan=request.POST.get('id'))
                penjualan.delete()

            else:
                to_database = Penjualan(request.POST)

                if to_database.is_valid():
                    to_database.instance.konsumen = Konsumen.objects.get(
                        id_konsumen=request.POST.get('id_konsumen'))
                    to_database.save()

                    insert_to_detail_penjualan = DetailFakturPenjualan.objects.create(
                        faktur_penjualan=FakturPenjualan.objects.get(
                            no_faktur_penjualan=to_database.instance.no_faktur_penjualan),
                        produk=Produk.objects.get(id_produk=request.POST.get('id_produk')),
                        kuantitas=request.POST.get('kuantitas'))
                    insert_to_detail_penjualan.save()

                    update_stok = DetailProduk.objects.get(produk=insert_to_detail_penjualan.produk.id_produk)
                    update_stok.stok -= int(request.POST.get('kuantitas'))
                    update_stok.save()

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
        table_pembelian = FakturPembelian.objects.order_by('no_faktur_pembelian').values(
            'no_faktur_pembelian', 'petugas__distributor__nama_distributor',
            'detailfakturpembelian__id_detail_faktur_pembelian',
            'tanggal_pembelian', 'detailfakturpembelian__produk__nama_produk',
            'detailfakturpembelian__kuantitas', 'detailfakturpembelian__harga_satuan',
            'detailfakturpembelian__produk__jenis_produk__nama_jenis_produk',
            'detailfakturpembelian__produk__detailproduk__tanggal_kadaluarsa',
            'detailfakturpembelian__produk__id_produk'
        )

        modal_edit_jenis_produk = [{'id_produk': item['detailfakturpembelian__produk__id_produk'],
                                    'kadaluarsa': str(
                                        item['detailfakturpembelian__produk__detailproduk__tanggal_kadaluarsa']),
                                    'jenis_produk': item[
                                        'detailfakturpembelian__produk__jenis_produk__nama_jenis_produk']}
                                   for item in table_pembelian]
        context['modal_edit_jenis_produk'] = modal_edit_jenis_produk

        for item in table_pembelian:
            if item.get('detailfakturpembelian__kuantitas'):
                item['total'] = item['detailfakturpembelian__kuantitas'] * item[
                    'detailfakturpembelian__harga_satuan']
            else:
                item['total'] = None

        context['table_pembelian'] = table_pembelian
        # end data table

        if request.POST:
            if 'delete' in request.POST:
                delete_pembelian = FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('id'))
                delete_pembelian.delete()

            elif 'update' in request.POST:

                id_global = request.POST.get('id').split('.')

                update_pemblian = FakturPembelian.objects.get(no_faktur_pembelian=id_global[0])
                update_pemblian.tanggal_pembelian = request.POST.get('tanggal_pembelian')
                update_pemblian.petugas = Petugas.objects.get(
                    distributor=Distributor.objects.get(id_distributor=request.POST.get('nama_distributor')))
                update_pemblian.save()

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

                update_harga_jual_to_database(request.POST.get('nama_produk'), request.POST.get('nama_jenis_produk'))

            else:

                insert_produk = Produk.objects. \
                    create(nama_produk=request.POST.get('nama_produk'),
                           jenis_produk=JenisProduk.objects.get(
                               id_jenis_produk=request.POST.get('nama_jenis_produk')))

                insert_faktur_pembelian = FakturPembelian.objects.create(
                    tanggal_pembelian=request.POST.get('tanggal_pembelian'),
                    tunai=float(request.POST.get('harga_satuan')) * float(request.POST.get('kuantitas')),
                    pengguna=request.user,
                    petugas=Petugas.objects.get(
                        distributor=Distributor.objects.get(id_distributor=request.POST.get('nama_distributor'))),
                )

                DetailFakturPembelian.objects.create(
                    faktur_pembelian=FakturPembelian.objects.get(
                        no_faktur_pembelian=insert_faktur_pembelian.no_faktur_pembelian),
                    produk=Produk.objects.get(id_produk=insert_produk.id_produk),
                    kuantitas=request.POST.get('kuantitas'),
                    harga_satuan=request.POST.get('harga_satuan')
                )

                DetailProduk.objects.create(
                    faktur_pembelian=FakturPembelian.objects.get(
                        no_faktur_pembelian=insert_faktur_pembelian.no_faktur_pembelian),
                    produk=Produk.objects.get(id_produk=insert_produk.id_produk),
                    stok=request.POST.get('kuantitas'),
                    tanggal_kadaluarsa=request.POST.get('tanggal_kadaluarsa'),
                    harga_jual_satuan=float(request.POST.get('harga_satuan')) * 0.2 + float(
                        request.POST.get('harga_satuan'))
                )

                update_harga_jual_to_database(request.POST.get('nama_produk'), request.POST.get('nama_jenis_produk'))
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

        produk = Produk.objects.order_by('id_produk').values(
            'id_produk', 'nama_produk', 'detailfakturpembelian__harga_satuan',
            'detailproduk__stok', 'jenis_produk__nama_jenis_produk',
            'detailproduk__tanggal_kadaluarsa', 'detailproduk__faktur_pembelian__no_faktur_pembelian'
        )
        context['produk'] = produk

        if request.POST:
            if 'delete' in request.POST:
                delete_produk = Produk.objects.get(id_produk=request.POST.get('id'))
                delete_produk.delete()

            elif 'update' in request.POST:
                produk = Produk.objects.get(id_produk=request.POST.get('id'))
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
