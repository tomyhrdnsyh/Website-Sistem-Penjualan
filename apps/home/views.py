# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from .models import *
from .form import Penjualan, FormDistributor
from datetime import datetime
from django.shortcuts import redirect


@login_required(login_url="/login/")
def index(request):
    # =================== chart penjualan =================
    # query database
    sales_invoice_detail = DetailFakturPenjualan.objects. \
        order_by('faktur_penjualan__tanggal_jual').values('id_detail_faktur_penjualan', 'kuantitas',
                                                      'faktur_penjualan__tanggal_jual',
                                                      'faktur_penjualan__konsumen__nama_konsumen')

    raw_penjualan = defaultdict(list)
    for item in sales_invoice_detail:
        raw_penjualan[item['faktur_penjualan__tanggal_jual']].append(item['kuantitas'])

    penjualan_data = [sum(item) for item in raw_penjualan.values()]
    penjualan_labels_line = [datetime.strftime(item, "%d-%m-%y") for item in raw_penjualan.keys()]
    penjualan_labels_pie = [item['faktur_penjualan__konsumen__nama_konsumen'] for item in sales_invoice_detail]

    # =================== chart pembelian =================
    # query database
    purchase_invoice = FakturPembelian.objects.order_by('tanggal_pembelian').values('tanggal_pembelian', 'tunai')
    pembelian_data = [item['tunai'] for item in purchase_invoice]
    pembelian_labels = [datetime.strftime(item['tanggal_pembelian'], "%d-%m-%y") for item in purchase_invoice]
    context = {'segment': 'index',
               'penjualan_data': penjualan_data,
               'penjualan_labels_line': penjualan_labels_line,
               'penjualan_labels_pie': penjualan_labels_pie,
               'pembelian_data': pembelian_data,
               'pembelian_labels': pembelian_labels}

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
        konsumen_choice = [{'value': item['nama_konsumen'], 'option': item['nama_konsumen'].title()}
                           for item in Konsumen.objects.values('nama_konsumen')]
        produk_choice = [{'value': item['nama_produk'], 'option': item['nama_produk'].title()}
                         for item in Produk.objects.values('nama_produk')]

        context['konsumen_form'] = konsumen_choice
        context['produk_form'] = produk_choice
        # end form modal

        context['form_penjualan'] = Penjualan

        sales = FakturPenjualan.objects. \
            order_by('no_faktur_penjualan').values('no_faktur_penjualan', 'konsumen__nama_konsumen',
                                                   'konsumen__alamat_konsumen',
                                                   'detailfakturpenjualan__produk__nama_produk',
                                                   'tanggal_jual', 'detailfakturpenjualan__kuantitas',
                                                   'detailfakturpenjualan__produk__detailproduk__harga_jual_satuan')

        context['penjualan'] = sales

        if request.POST:
            if 'update' in request.POST:
                penjualan = FakturPenjualan.objects.get(no_faktur_penjualan=request.POST.get('id'))
                penjualan.konsumen = Konsumen.objects.get(nama_konsumen=request.POST.get('konsumen'))
                penjualan.tanggal_jual = request.POST.get('tanggal_jual')

                detail_penjualan = DetailFakturPenjualan.objects.get(faktur_penjualan=penjualan.no_faktur_penjualan)
                detail_penjualan.kuantitas = request.POST.get('kuantitas')
                detail_penjualan.produk = Produk.objects.get(nama_produk=request.POST.get('produk'))

                penjualan.save()
                detail_penjualan.save()

            elif 'delete' in request.POST:
                penjualan = FakturPenjualan.objects.get(no_faktur_penjualan=request.POST.get('id'))
                penjualan.delete()

            else:
                to_database = Penjualan(request.POST)
                if to_database.is_valid():
                    to_database.instance.konsumen = Konsumen.objects.get(nama_konsumen=request.POST.get('konsumen'))
                    to_database.save()
                    insert_to_detail_penjualan = DetailFakturPenjualan.objects.create(
                        faktur_penjualan=FakturPenjualan.objects.latest('no_faktur_penjualan'),
                        produk=Produk.objects.get(nama_produk=request.POST.get('produk')),
                        kuantitas=request.POST.get('kuantitas'))
                    insert_to_detail_penjualan.save()
            return redirect('/penjualan.html')
    # ====== END MENU PENJUALAN ======

    # ====== MENU PEMBELIAN ======
    if load_template == 'pembelian.html' or load_template == 'pdf-pembelian.html':
        # form add data
        nama_distributor = Distributor.objects.values('nama_distributor')
        petugas = Petugas.objects.values('nama_petugas')
        jenis_produk = JenisProduk.objects.values('nama_jenis_produk')

        context['nama_distributor'] = nama_distributor
        context['petugas'] = petugas
        context['jenis_produk'] = jenis_produk
        # end form add data

        # data table
        table_pembelian = FakturPembelian.objects.order_by('no_faktur_pembelian').values(
            'no_faktur_pembelian', 'petugas__distributor__nama_distributor',
            'tanggal_pembelian', 'detailfakturpembelian__produk__nama_produk',
            'detailfakturpembelian__kuantitas', 'detailfakturpembelian__harga_satuan'
        )
        context['table_pembelian'] = table_pembelian
        # end data table
        if request.POST:
            if 'delete' in request.POST:
                delete_pembelian = FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('id'))
                delete_pembelian.delete()

            else:

                # 'nama_distributor': ['CINTA TANI'], 'nama_petugas': ['WENDI'], 'tanggal_pembelian': [
                #     '2022-11-22'], 'nama_jenis_produk': ['Fungisida'], 'nama_produk': ['Pare Booster '],
                #     'kuantitas': ['12'], 'harga_satuan': ['10000'], 'tanggal_kadaluarsa': ['2022-12-10']}
                insert_produk = Produk.objects. \
                    create(nama_produk=request.POST.get('nama_produk'),
                           jenis_produk=JenisProduk.objects.get(
                               nama_jenis_produk=request.POST.get('nama_jenis_produk')))
                insert_produk.save()

                insert_faktur_pembelian = FakturPembelian.objects.create(
                    tanggal_pembelian=request.POST.get('tanggal_pembelian'),
                    tunai=float(request.POST.get('harga_satuan'))*float(request.POST.get('kuantitas')),
                    pengguna=request.user,
                    petugas=Petugas.objects.get(nama_petugas=request.POST.get('nama_petugas')),

                )
                insert_faktur_pembelian.save()
                insert_detail_faktur_pembelian = DetailFakturPembelian.objects.create(
                    faktur_pembelian=FakturPembelian.objects.latest('no_faktur_pembelian'),
                    produk=Produk.objects.get(nama_produk=request.POST.get('nama_produk')),
                    kuantitas=request.POST.get('kuantitas'),
                    harga_satuan=request.POST.get('harga_satuan')
                )
                insert_detail_faktur_pembelian.save()

                insert_detail_produk = DetailProduk.objects.create(
                    faktur_pembelian=FakturPembelian.objects.latest('no_faktur_pembelian'),
                    produk=Produk.objects.latest('id_produk'),
                    stok=request.POST.get('kuantitas'),
                    tanggal_kadaluarsa=request.POST.get('tanggal_kadaluarsa'),
                    harga_jual_satuan=float(request.POST.get('harga_satuan')) * 0.2 + float(
                        request.POST.get('harga_satuan'))
                )
                insert_detail_produk.save()


            return redirect('/pembelian.html')

    # ====== END MENU PEMBELIAN ======

    # ====== MENU PRODUK ======

    if load_template == 'product.html' or load_template == 'pdf-penjualan.html':
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

                detail_faktur_pembelian = DetailFakturPembelian.objects.get(produk=produk)
                detail_faktur_pembelian.faktur_pembelian = FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('no_faktur_pembelian'))
                detail_faktur_pembelian.kuantitas = request.POST.get('kuantitas')
                detail_faktur_pembelian.harga_satuan = request.POST.get('harga_satuan')
                detail_faktur_pembelian.save()


                detail_produk = DetailProduk.objects.get(produk=produk)
                detail_produk.faktur_pembelian = FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('no_faktur_pembelian'))
                detail_produk.stok = request.POST.get('kuantitas')
                detail_produk.tanggal_kadaluarsa = request.POST.get('tanggal_kadaluarsa')
                detail_produk.harga_jual_satuan = float(request.POST.get('harga_satuan'))*0.2+float(request.POST.get('harga_satuan'))
                detail_produk.save()

            else:
                insert_produk = Produk.objects.\
                    create(nama_produk=request.POST.get('nama_produk'),
                           jenis_produk=JenisProduk.objects.get(nama_jenis_produk=request.POST.get('jenis_produk')))
                insert_produk.save()

                insert_detail_faktur_pembelian = DetailFakturPembelian.objects.create(
                    faktur_pembelian=FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('no_faktur_pembelian')),
                    produk=Produk.objects.latest('id_produk'),
                    kuantitas=request.POST.get('kuantitas'),
                    harga_satuan=request.POST.get('harga_satuan')
                )
                insert_detail_faktur_pembelian.save()

                insert_detail_produk = DetailProduk.objects.create(
                    faktur_pembelian=FakturPembelian.objects.get(no_faktur_pembelian=request.POST.get('no_faktur_pembelian')),
                    produk=Produk.objects.latest('id_produk'),
                    stok=request.POST.get('kuantitas'),
                    tanggal_kadaluarsa=request.POST.get('tanggal_kadaluarsa'),
                    harga_jual_satuan=float(request.POST.get('harga_satuan'))*0.2+float(request.POST.get('harga_satuan'))
                )
                insert_detail_produk.save()

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
                print(request.POST)
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
