from django.urls import path
from . import views

urlpatterns = [
    path('no_faktur/', views.no_faktur),
    path('jenis_produk/', views.jenis_produk),
    path('add_produk/', views.addProduk),
    path('auth/', views.auth),
]