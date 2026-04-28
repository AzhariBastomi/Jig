# 🛠️ Panduan Pengujian (Testing Guide) Aplikasi Task Manager

Aplikasi ini dibangun menggunakan arsitektur **Modular OOP / MVC (Model-View-Controller)**. UI (Antarmuka) dan Worker (Mesin Backend) dipisahkan secara total menggunakan prinsip *Dependency Injection*.

Hal ini memungkinkan kita untuk melakukan tes pada masing-masing komponen secara independen tanpa harus menyalakan seluruh aplikasi.

## 📌 Persiapan Penting
- Pastikan posisi terminal Anda selalu berada di *root folder* proyek sebelum menjalankan perintah apa pun:
    ```bash
    cd ~/Jig

## 1. 🚀 Menjalankan Aplikasi Penuh (Production Mode)
- Menjalankan aplikasi secara utuh di mana Antarmuka (UI) dan Mesin (Worker) sudah saling terhubung. Semua tombol "Start" akan benar-benar mengeksekusi mesin/script di belakang layar.
    ```bash
    python main.py
- Cara Keluar: Tekan tombol Esc di keyboard atau klik tombol Keluar di pojok kanan atas.
- Catatan: Jangan gunakan Ctrl+C jika sedang berada di mode Fullscreen tanpa mengaktifkan trik interrupt Tkinter.

## 2. 🎨 Mengetes Antarmuka Saja (UI Sandbox Mode)
- Menjalankan dummy UI yang terisolasi 100% dari sistem backend. Sangat berguna untuk mendesain tata letak (layout), menguji warna, atau melihat animasi progress bar tanpa khawatir membebani memori CPU atau mengalami error library (seperti hcitool).

    ```bash
    python -m ui.app
- Hasil: Aplikasi akan terbuka dengan data FakeTask (Tugas Bohongan). Tombol Start hanya akan menjalankan animasi visual Tkinter.

## 3. ⚙️ Mengetes Mesin Pekerja (Worker Testing / No UI)
- Menjalankan program mesin murni melalui terminal. UI Tkinter tidak akan terbuka sama sekali. Sangat berguna untuk melakukan debugging logika program, perhitungan persentase, atau memastikan koneksi perangkat keras (Bluetooth/Modbus) berjalan mulus sebelum digabungkan ke UI.
    ```bash
    # Mengetes logika download (Progress Bar Layout)
    python -m worker.download_task

    # Mengetes perintah terminal (Button OK/NG Layout)
    python -m worker.command_task
- Hasil: Progress bar dan log aktivitas akan dicetak langsung di terminal (stdout).

## 4. 🗔 Mengetes Dialog Menu (Dialog Sandbox)
- Menjalankan jendela pop-up dialog secara independen untuk menguji tata letak kartu menu, fungsi hover, dan fitur gulir (scrollbar).
    ```bash
    python -m ui.dialogs
- Hasil: Akan muncul jendela "Simulasi App Utama" diikuti dengan jendela pop-up "Tambah Task Baru" yang berisi menu-menu percobaan. Hasil klik akan dicetak di terminal.

# 💡 Mengapa Menggunakan Flag -m?
- Beberapa perintah di atas menggunakan python -m nama_folder.nama_file. Huruf -m adalah singkatan dari module.

- Hal ini menginstruksikan Python untuk tetap membaca folder ~/Jig sebagai direktori utama (root), sehingga fungsi import config atau eksekusi relative import (from .base_task import...) tidak akan mengalami ModuleNotFoundError. Selalu gunakan cara ini saat mengetes script yang berada di dalam sub-folder!


***

Semoga dokumen panduan ini membuat proyek **Jig** milik Mas Azhari semakin rapi layakny