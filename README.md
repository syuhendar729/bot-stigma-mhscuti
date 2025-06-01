# Bot Stigma - MhsCuti

[![Python](https://img.shields.io/badge/Python-3.8-blue.svg)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Request-2.31.0-green.svg)](https://www.pygame.org/)
[![Version](https://img.shields.io/badge/Version-1.0-orange.svg)]()

## Algoritma Greedy dalam Bot Diamond Game

Bot ini mengimplementasikan algoritma greedy untuk mengoptimalkan pengumpulan diamond dalam permainan. Strategi greedy yang digunakan mempertimbangkan berbagai faktor untuk pengambilan keputusan yang efisien dan efektif.

### Strategi Greedy yang Diimplementasikan

Setelah mempertimbangkan seluruh alternatif dan menganalisis efektivitasnya, kami memilih strategi greedy dengan kombinasi strategi di bawah ini:

1. **Skor/Jarak**: Digunakan sebagai fungsi seleksi utama untuk menentukan target optimal di setiap giliran
2. **Manajemen Inventory**: Bot akan kembali ke base ketika kapasitas inventory melebih 80% untuk mencegah kehilangan skor
3. **Menggunakan teleport** sebagai jalan pintas untuk mencapai target.

Dengan strategi ini, bot tidak hanya efisien dalam mengumpulkan skor, tetapi juga memiliki mekanisme defensif yang meningkatkan keberlangsungan permainan.

## Requirement Program

- Python 3.8 atau lebih baru
- Library `requests` untuk API calls
- Server API diamond game yang berjalan (lokal atau remote)

## Instalasi dan Menjalankan Program

1. Clone repository ini:
```bash
git clone https://github.com/syuhendar729/bot-stigma-mhscuti.git
cd bot-stigma-mhscuti
```
2. Install dependency yang diperlukan:
```bash
pip install -r requirements.txt
```
3. Edit file main.py pada baris 312 untuk mengubah base_url sesuai dengan URL board Etimo Diamond dan API bot yang telah Anda daftarkan:
```bash
# Ubah URL ini dengan URL board dan API bot Anda
base_url = "http://[url_board_etimo_diamond]/api/bots/[api_key_bot_anda]"
```
4. Jalankan program:
```bash
python main.py
```

## Author
<table> <tr> <td align="center"> <a href="https://github.com/syuhendar729"> <img src="https://github.com/syuhendar729.png" width="100px;" alt="Syuhada Rantisi"/> <br /> <sub><b>Syuhada Rantisi</b></sub> </a> <br /> <sub>122140092</sub> </td> <td align="center"> <a href="https://github.com/Randyh-25"> <img src="https://github.com/Randyh-25.png" width="100px;" alt="Randy Hendriyawan"/> <br /> <sub><b>Randy Hendriyawan</b></sub> </a> <br /> <sub>122140171</sub> </td> <td align="center"> <a href="https://github.com/MuhammadRiveldo"> <img src="https://github.com/MuhammadRiveldo.png" width="100px;" alt="Muhammad Riveldo"/> <br /> <sub><b>Muhammad Riveldo H.P</b></sub> </a> <br /> <sub>122140037</sub> </td> </tr> </table>

