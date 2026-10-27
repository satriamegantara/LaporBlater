# PRD: Sistem Informasi Geografis Pengaduan Kerusakan Fasilitas Umum di Blater Berbasis WebGIS

| Item | Keterangan |
|---|---|
| Versi dokumen | 1.1 |
| Jenis produk | Purwarupa (prototype) aplikasi web |
| Wilayah studi | Desa Blater, Kecamatan Kalimanah, Kabupaten Purbalingga, Jawa Tengah |
| Institusi | Universitas Jenderal Soedirman, Fakultas Teknik, Program Studi Informatika |
| Tim | Satria Megantara Wildan (H1D024022), Zaki Fatah Alfikri (H1D024124), Aldi Trio Prabowo (H1D025027) |
| Bahasa antarmuka | Bahasa Indonesia |
| Sumber acuan | Laporan Proyek Sistem Informasi Geografis (Bab I sampai Bab III) |

---

## 1. Ringkasan Produk

Aplikasi WebGIS yang memungkinkan warga Desa Blater melaporkan kerusakan fasilitas umum melalui peta interaktif dengan titik lokasi, foto, dan jenis kerusakan. Sistem memvalidasi lokasi terhadap batas desa, mengklasifikasikan foto secara otomatis dengan model AI sebagai informasi pendukung, menganalisis pola persebaran laporan (KDE, DBSCAN, Getis-Ord Gi*), dan menghitung skor prioritas penanganan. Pengelola (perangkat desa) memantau laporan melalui dasbor dan memperbarui status penanganan.

Fasilitas yang dicakup ada tiga jenis:
1. **Jalan**: kerusakan badan jalan (berlubang, amblas, retak)
2. **PJU** (Penerangan Jalan Umum): lampu padam, tiang rusak
3. **Drainase**: tersumbat sampah atau endapan, tanggul jebol

Sistem berupa **purwarupa**. Modul penganggaran desa (e-budgeting) tidak termasuk dalam lingkup.

---

## 2. Latar Belakang dan Masalah

Pelaporan kerusakan saat ini berjalan lewat lisan ke perangkat desa atau pesan di grup warga. Masalah yang dihadapi:

1. Lokasi tidak akurat. Laporan hanya menyebut patokan lokal yang ambigu, tanpa koordinat.
2. Bukti foto tercecer dan tidak terhubung dengan laporan maupun lokasinya.
3. Tidak ada dasbor spasial, sehingga klaster kerusakan sulit terlihat dan prioritas perbaikan tidak objektif.
4. Kategori dari pelapor tidak divalidasi, dan tingkat keparahan dinilai subjektif.

Penelitian terdahulu (MySIGSAG, CitySolution, Sasmito et al.) belum menggabungkan pelaporan warga, klasifikasi foto, dan analisis hotspot untuk beberapa jenis fasilitas pada skala desa. Sistem ini mengisi celah tersebut.

---

## 3. Tujuan dan Target

### 3.1 Tujuan
- Menyediakan kanal pengaduan berbasis lokasi yang mudah diakses dari ponsel.
- Mengenali jenis kerusakan dari foto secara otomatis sebagai dukungan keputusan.
- Menampilkan pola persebaran, klaster, dan skor prioritas penanganan.
- Memantau status penanganan dari laporan masuk sampai selesai.

### 3.2 Target Terukur

| Aspek | Metode | Metrik | Target |
|---|---|---|---|
| Kinerja model AI | Evaluasi pada data uji terpisah | F1-score makro | ≥ 0,80 dan lebih tinggi dari baseline |
| Akurasi posisi | Bandingkan dengan koordinat GNSS (minimal 30 titik) | RMSE (meter) per sumber lokasi | Dilaporkan per sumber; ≤ 10 m dianggap layak |
| Fungsionalitas | Pengujian black-box | Persentase skenario lulus | 100% skenario inti |
| Kinerja kueri | EXPLAIN ANALYZE dengan dan tanpa indeks GiST, pada 1.000 / 10.000 / 100.000 titik sintetis | Waktu eksekusi (ms) | Indeks mempercepat kueri radius |
| Kegunaan | Kuesioner SUS, minimal 20 responden (warga, mahasiswa kost, perangkat desa) | Skor SUS 0–100 | ≥ 68 |

---

## 4. Pengguna dan Peran

| Peran | Deskripsi | Hak akses utama |
|---|---|---|
| **Warga** | Pelapor, termasuk mahasiswa kost dan pelaku usaha mikro | Membuat laporan, melihat peta dan status laporan publik, memfilter peta |
| **Petugas/Pengelola** (perangkat desa) | Memverifikasi dan menangani laporan | Semua hak warga, plus memverifikasi laporan, mengubah status, melihat identitas pelapor, melihat dasbor prioritas |
| **Admin** | Pengelola sistem teknis (tim proyek) | Mengelola jenis fasilitas, pengguna pengelola, dan parameter analisis (bobot prioritas, eps DBSCAN, bandwidth KDE) |

> **Keputusan**: warga dapat melapor secara anonim tanpa akun. Kontak (nama, telepon) bersifat opsional. Pengelola dan admin wajib login dengan akun.

---

## 5. Lingkup

### 5.1 Dalam lingkup (In Scope)
- Formulir pengaduan berbasis peta dengan tiga cara penentuan lokasi.
- Unggah foto dengan ekstraksi metadata EXIF.
- Validasi lokasi terhadap batas Desa Blater.
- Deteksi laporan ganda dalam radius 6 meter untuk kategori yang sama.
- Klasifikasi foto ke empat kelas, dengan tingkat keyakinan.
- Alur status laporan dan riwayat perubahan.
- Peta dengan layer, filter, peta panas (KDE), dan klaster (DBSCAN).
- Statistik hotspot Getis-Ord Gi* pada layer analisis.
- Dasbor ringkasan dan daftar prioritas penanganan.
- Penyimpanan data spasial di PostgreSQL/PostGIS dengan EPSG:4326.

### 5.2 Di luar lingkup (Out of Scope)
- Modul penganggaran desa (e-budgeting).
- Notifikasi push atau Firebase (disarankan sebagai pengembangan lanjutan).
- Analisis jaringan untuk rute kunjungan perbaikan (F-22, ditunda).
- Pelaporan berbasis teks tanpa foto atau lokasi sebagai kategori tersendiri.
- Aplikasi Android native. Antarmuka berupa web responsif.
- Deteksi kerusakan dan tingkat keparahan secara penuh pada kelas PJU dan drainase (hanya klasifikasi).
- Deteksi objek pada kelas jalan sebagai fitur wajib (hanya eksplorasi, lihat bagian 8.5).
- Otomasi keputusan. Prediksi AI tidak menggantikan keputusan pengelola.

---

## 6. Arsitektur Teknis

Arsitektur client-server tiga lapisan.

| Lapisan | Teknologi | Peran |
|---|---|---|
| Presentation | HTML, CSS, JavaScript, Leaflet.js, OpenStreetMap | Peta interaktif, formulir, dasbor. Responsif untuk ponsel dan desktop |
| Application | Python Flask (REST API) | Endpoint pelaporan, validasi lokasi, pemrosesan foto, pemanggilan layanan inferensi, perhitungan skor prioritas |
| Data | PostgreSQL + PostGIS | Penyimpanan data spasial dan relasional, indeks GiST, fungsi spasial |
| AI service | Python, TensorFlow/Keras, MobileNetV2 / EfficientNet-B0 | Klasifikasi foto. Dipisah sebagai modul sehingga model bisa diganti tanpa mengubah antarmuka |
| Analisis spasial | Python dengan pustaka statistik spasial (misalnya PySAL, scikit-learn untuk DBSCAN, SciPy/scikit-learn untuk KDE) | KDE, DBSCAN, Getis-Ord Gi*, Moran's I lokal |
| Pemrosesan foto | Pustaka Python pembaca EXIF (misalnya Pillow atau exifread) | Ekstraksi latitude, longitude, dan waktu |
| Deteksi objek (eksplorasi) | YOLOv8 (Ultralytics) | Opsional, untuk kelas jalan saja |
| Kolaborasi | Git dan GitHub, cabang terpisah per modul (basis data, model AI, API, antarmuka) | Pengelolaan kode tim |

### 6.1 Sistem Referensi Koordinat
- Penyimpanan dan tampilan: **WGS 84 (EPSG:4326)** untuk semua layer.
- Perhitungan jarak dan luas: **UTM zona 49S (EPSG:32749)**, agar satuan dalam meter.
- Transformasi dilakukan saat data masuk dari sumber lain.

### 6.2 Metodologi Pengembangan
Prototyping iteratif. Setiap iterasi terdiri dari analisis kebutuhan, perancangan, implementasi, dan pengujian oleh tim serta calon pengguna. Hasilnya menjadi masukan iterasi berikutnya.

---

## 7. Model Data

Skema basis data terdiri dari enam tabel: `users`, `facility_types`, `report_status`, `reports`, `photos`, dan `ai_predictions`. Kolom di bawah adalah rancangan awal dan boleh disesuaikan saat implementasi, selama konsep dan relasinya tetap.

### 7.1 `facility_types`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| code | VARCHAR(20) UNIQUE | `JALAN`, `PJU`, `DRAINASE` |
| name | VARCHAR(100) | Nama tampilan |
| is_active | BOOLEAN | |

Nilai awal: Jalan, PJU, Drainase.

### 7.2 `report_status`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| code | VARCHAR(30) UNIQUE | `MENUNGGU_VERIFIKASI`, `DIVERIFIKASI`, `DIPROSES`, `SELESAI` |
| name | VARCHAR(100) | |
| sort_order | INT | Urutan alur |

Alur status: **Menunggu verifikasi → Diverifikasi → Diproses → Selesai**.

### 7.3 `users`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| name | VARCHAR(150) | |
| email | VARCHAR(150) UNIQUE NULL | Opsional untuk warga |
| phone | VARCHAR(30) NULL | Opsional |
| password_hash | VARCHAR(255) NULL | Wajib untuk pengelola/admin |
| role | ENUM | `warga`, `pengelola`, `admin` |
| created_at | TIMESTAMP | |

### 7.4 `reports`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| reporter_id | INT FK users NULL | Null jika anonim |
| facility_type_id | INT FK facility_types | Kategori yang dipilih pelapor |
| ai_category_id | INT FK facility_types NULL | Hasil klasifikasi terakhir (diisi dari ai_predictions) |
| status_id | INT FK report_status | |
| severity | ENUM NULL | `ringan`, `sedang`, `berat`. Diisi pengelola, dengan saran dari AI atau pelapor |
| description | TEXT | |
| location | GEOMETRY(Point, 4326) NOT NULL | Indeks GiST wajib |
| location_source | ENUM | `exif`, `device_gps`, `manual_map` |
| source_type | ENUM | `warga`, `survei_tim`. Membedakan laporan warga dari data survei |
| is_duplicate_of | INT FK reports NULL | Terisi jika terdeteksi duplikat |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

Indeks: GiST pada `location`; B-tree pada `status_id`, `facility_type_id`, `created_at`.

### 7.5 `photos`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| report_id | INT FK reports ON DELETE CASCADE | |
| file_path | VARCHAR(255) | Lokasi berkas tersimpan |
| public_path | VARCHAR(255) | Versi tanpa EXIF dan dengan wajah/plat disamarkan, untuk tampilan publik |
| exif_lat | DOUBLE PRECISION NULL | |
| exif_lng | DOUBLE PRECISION NULL | |
| exif_taken_at | TIMESTAMP NULL | |
| width, height | INT | Ukuran asli |
| uploaded_at | TIMESTAMP | |

### 7.6 `ai_predictions`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| photo_id | INT FK photos | |
| predicted_class | VARCHAR(30) | `JALAN_RUSAK`, `PJU_RUSAK`, `DRAINASE_TERSUMBAT`, `KONDISI_NORMAL` |
| confidence | NUMERIC(5,4) | 0–1 |
| model_name | VARCHAR(50) | Contoh: `mobilenetv2` |
| model_version | VARCHAR(30) | Untuk ketertelusuran |
| created_at | TIMESTAMP | |

### 7.7 `report_status_history` (tambahan)
Mencatat setiap perubahan status: `report_id`, `from_status_id`, `to_status_id`, `changed_by`, `note`, `changed_at`. Dibutuhkan untuk dasbor status dan audit.

---

## 8. Fitur dan Kebutuhan Fungsional

Setiap fitur diberi kode `F-xx` dan prioritas: **M** (wajib untuk rilis purwarupa), **S** (sebaiknya ada), **C** (opsional).

### 8.1 Pelaporan Warga

**F-01 Formulir pengaduan (M)**
- Pelapor memilih jenis fasilitas (Jalan, PJU, Drainase), mengisi deskripsi, dan mengunggah foto.
- Formulir tidak boleh dikirim tanpa jenis fasilitas, lokasi, dan minimal satu foto.
- Deskripsi maksimal 500 karakter.

**F-02 Penentuan lokasi (M)**
Tiga cara, dengan urutan prioritas:
1. **Metadata EXIF foto**: koordinat dibaca otomatis dari foto. Jika ada, titik langsung terisi.
2. **Geolokasi perangkat**: menggunakan `navigator.geolocation` setelah izin pengguna. Akurasi ditampilkan ke pengguna.
3. **Pilih titik manual di peta**: pelapor mengklik atau menyeret penanda pada peta.

Jika foto tidak memiliki EXIF, sistem tidak menolak foto. Sistem meminta lokasi dari geolokasi atau titik manual.

**F-03 Validasi lokasi terhadap batas desa (M)**
- Koordinat diuji dengan `ST_Within` terhadap poligon batas Desa Blater.
- Laporan di luar batas desa **ditolak total** dan tidak disimpan ke basis data. Pelapor menerima pesan yang menjelaskan bahwa lokasi berada di luar wilayah Desa Blater.
- Koordinat dengan nilai di luar rentang wajar (lintang -90..90, bujur -180..180) ditolak.

**F-04 Ekstraksi EXIF (M)**
- Pustaka pembaca EXIF mengambil latitude, longitude, dan waktu pengambilan.
- Format derajat-menit-detik dikonversi ke derajat desimal.
- Foto disimpan dalam dua versi: asli (akses terbatas pengelola) dan publik (EXIF dihapus).

**F-05 Deteksi laporan ganda (S)**
- Sebelum menyimpan, sistem mencari laporan dengan kategori sama dalam radius 6 meter menggunakan `ST_DWithin` pada UTM (EPSG:32749). Jika 6 meter terbukti terlalu sempit atau terlalu dekat saat pengujian, radius diganti 10 meter.
- Jika ada, pelapor diberi tahu dan dapat memilih "tambahkan sebagai foto tambahan" atau "tetap kirim".

**F-06 Konfirmasi dan tanda terima (M)**
- Setelah kirim, pelapor mendapat ID laporan dan tautan untuk memantau status.

### 8.2 Klasifikasi Foto Berbasis AI

**F-07 Klasifikasi empat kelas (M)**
- Kelas: `JALAN_RUSAK`, `PJU_RUSAK`, `DRAINASE_TERSUMBAT`, `KONDISI_NORMAL`.
- Dijalankan otomatis setelah foto diunggah, secara asinkron agar pelapor tidak menunggu.
- Hasil disimpan di `ai_predictions` dengan confidence dan versi model.

**F-08 Validasi dan saran kategori (M)**
- Jika prediksi AI berbeda dengan kategori pilihan pelapor dan confidence di atas ambang (0,85), pelapor diberi saran: "Foto ini tampak seperti *PJU rusak*. Ubah kategori?"
- Pelapor tetap bisa mempertahankan pilihannya. Prediksi AI tetap tersimpan sebagai informasi pendukung.
- Ambang 0,85 adalah nilai yang disepakati dan dapat diubah lewat konfigurasi.

**F-09 Tampilan prediksi bagi pengelola (M)**
- Pengelola melihat kelas prediksi dan confidence di halaman detail laporan.
- Pengelola dapat menyetujui atau mengubah kategori.

**F-10 Antarmuka layanan inferensi (M)**
- Layanan AI dipanggil lewat satu antarmuka (misalnya fungsi `predict(image) -> {class, confidence, model_version}`).
- Implementasi model dapat diganti tanpa mengubah antarmuka dan endpoint.

### 8.3 Pengelolaan Laporan oleh Pengelola

**F-11 Daftar laporan (M)**
- Tabel laporan dengan kolom: ID, jenis, kategori AI, status, tingkat keparahan, tanggal, dan skor prioritas.
- Pagination dan pengurutan.

**F-12 Perubahan status (M)**
- Pengelola mengubah status sesuai alur. Status tidak boleh melompat (misalnya dari Menunggu verifikasi langsung ke Selesai).
- Setiap perubahan wajib mencatat catatan (opsional), pengguna, dan waktu.
- Hanya pengelola dan admin yang bisa mengubah status.

**F-13 Penetapan tingkat keparahan (M)**
- Pengelola memilih ringan, sedang, atau berat.
- Sistem menampilkan saran dari pelapor dan dari AI sebagai referensi.

**F-14 Detail laporan (M)**
- Peta kecil dengan posisi laporan, foto (versi yang sesuai peran), deskripsi, riwayat status, dan prediksi AI.
- Identitas pelapor hanya terlihat oleh pengelola.

### 8.4 Peta Interaktif WebGIS

**F-15 Peta dasar dan layer (M)**
- Peta dasar OpenStreetMap.
- Layer: batas desa (poligon), jaringan jalan (garis), laporan (titik).
- Kontrol layer untuk menampilkan atau menyembunyikan tiap layer.
- Atribusi OpenStreetMap wajib ditampilkan.

**F-16 Penanda laporan (M)**
- Warna atau ikon membedakan jenis fasilitas.
- Penanda dapat diklik untuk membuka ringkasan laporan.
- Ukuran atau gaya penanda menunjukkan status atau keparahan.

**F-17 Filter (M)**
- Berdasarkan jenis fasilitas, status, tingkat keparahan, dan rentang tanggal.
- Filter diterapkan langsung pada peta dan daftar.

**F-18 Peta panas KDE (S)**
- Permukaan kepadatan dihitung dari titik laporan.
- Bandwidth diuji pada beberapa nilai dalam rentang puluhan hingga ratusan meter. Nilai default sekitar 100 m, dapat diubah admin.
- Layer ini dapat dinyalakan dan dimatikan.

**F-19 Klaster DBSCAN (S)**
- Titik dikelompokkan berdasarkan jarak dan kepadatan.
- Parameter `eps` dan `minPts` ditentukan melalui grafik jarak tetangga terdekat, lalu ditinjau secara visual di peta.
- Hasil klaster ditampilkan dengan warna berbeda dan jumlah laporan per klaster.

**F-20 Hotspot Getis-Ord Gi* (S)**
- Dihitung pada titik atau agregasi sesuai sel, menghasilkan z-score dan p-value.
- Hotspot ditampilkan hanya jika signifikan secara statistik (misalnya p < 0,05).

**F-21 Buffer dan overlay (C)**
- Buffer di sekitar fasilitas sensitif (kampus, permukiman kost). Contoh: radius 200 m, dipakai untuk bobot risiko keselamatan.

**F-22 Analisis jaringan untuk rute kunjungan (C, ditunda)**
- Rute kunjungan perbaikan disusun di atas jaringan jalan dari titik prioritas tertinggi.
- Fitur ini **ditunda** ke pengembangan lanjutan dan tidak termasuk rilis purwarupa ini.

### 8.5 Dasbor dan Skor Prioritas

**F-23 Ringkasan status (M)**
- Jumlah laporan per status, per jenis fasilitas, dan per bulan.
- Diagram batang atau donat.

**F-24 Skor prioritas (M)**
Skor dihitung sebagai jumlah terbobot dari empat kriteria yang masing-masing dinormalisasi ke rentang 0–1:

```
S = 0,35 × Keparahan + 0,30 × Kepadatan + 0,20 × Risiko_Keselamatan + 0,15 × Lama_Belum_Ditangani
```

| Kriteria | Indikator | Bobot awal | Cara normalisasi |
|---|---|---|---|
| Keparahan | Ringan = 0,33; sedang = 0,66; berat = 1,00 (dari keputusan pengelola, atau saran AI bila belum ditetapkan) | 0,35 | Nilai tetap |
| Kepadatan | Nilai KDE atau ukuran klaster DBSCAN di sekitar titik | 0,30 | Min-max terhadap seluruh laporan aktif |
| Risiko keselamatan | Jenis fasilitas dan kedekatan dengan kampus atau permukiman | 0,20 | Jenis: PJU dan jalan berat lebih tinggi; kedekatan dihitung dengan jarak (buffer) |
| Lama belum ditangani | Selisih hari sejak laporan dibuat | 0,15 | Min-max terhadap seluruh laporan aktif |

- Laporan berstatus Selesai tidak ikut dihitung.
- Bobot dapat diubah admin. Sistem menyediakan fitur uji sensitivitas: bobot diubah sekitar ±5% untuk melihat apakah urutan 10 teratas berubah.
- Daftar prioritas diurutkan dari skor tertinggi.

**F-25 Daftar prioritas (M)**
- 10 laporan teratas dengan skor, alasan utama (kriteria terbesar), dan tautan ke detail.

### 8.6 Antarmuka Warga: Pemantauan Status

**F-26 Cek status laporan (M)**
- Warga memasukkan ID laporan atau membuka tautan untuk melihat status dan riwayat perubahan.
- Tanpa identitas pelapor dan tanpa EXIF.

**F-27 Peta laporan publik (S)**
- Warga melihat sebaran laporan dan statusnya, tanpa foto asli dan tanpa data pribadi.

### 8.7 Pengelolaan Admin

**F-28 Kelola jenis fasilitas (S)**
**F-29 Kelola pengguna pengelola (M)**
**F-30 Konfigurasi parameter analisis (S)**: bobot prioritas, eps dan minPts DBSCAN, bandwidth KDE, ambang confidence AI.
**F-31 Log aktivitas (S)**: perubahan status, perubahan parameter, dan login pengelola.

---

## 9. Kebutuhan Data Spasial

| Data | Geometri / Format | Sumber | Catatan |
|---|---|---|---|
| Laporan kerusakan | Point (PostGIS) | Warga melalui WebGIS, dan survei tim | Atribut `source_type` membedakan keduanya |
| Foto | JPEG + EXIF | Unggahan warga, survei tim | Versi asli dan publik |
| Batas administrasi desa | Polygon / MultiPolygon (GeoJSON, SHP) | Data batas wilayah dan digitasi | Dipakai untuk validasi lokasi dan area studi |
| Jaringan jalan | LineString (GeoJSON, SHP) | OpenStreetMap (file `.osm.pbf` dari Geofabrik) | Dipakai untuk layer jalan dan analisis jaringan |
| Citra satelit dan DEM | Raster | Citra terbuka dan SRTM | Konteks tambahan, tidak wajib untuk M |
| Koordinat referensi | Point | Pengukuran GNSS di lapangan | Ground truth akurasi posisi |

### 9.1 Pembersihan Data Vektor
- Hapus geometri tidak valid dan duplikat. Gunakan `ST_IsValid` dan `ST_MakeValid`.
- Hapus fitur di luar batas desa.
- Normalisasi atribut kondisi ke kategori baku: **ringan, sedang, berat**.

---

## 10. Pipeline Model AI

### 10.1 Data Latih
- Sumber pra-latih: RDD2022 (47.420 citra jalan, enam negara) untuk kelas jalan.
- Sumber lokal: survei tim Desa Blater untuk ketiga kelas fasilitas dan kelas kondisi normal.
- Target awal: minimal 200 citra per kelas, seimbang antar kelas.
- Citra diberi label oleh dua anggota secara terpisah. Perbedaan label diselesaikan lewat diskusi.

### 10.2 Pra-pemrosesan
- Hapus berkas rusak dan duplikat.
- Ubah ukuran menjadi 224 × 224 piksel untuk klasifikasi (640 × 640 untuk deteksi objek).
- Normalisasi sesuai arsitektur.

### 10.3 Pembagian Data
- 70% latih, 15% validasi, 15% uji. Berstrata per kelas.
- **Pembagian berdasarkan lokasi pengambilan**: foto dari titik yang sama tidak boleh muncul di data latih dan data uji sekaligus.
- Augmentasi (pembalikan, rotasi kecil, perubahan kecerahan, penskalaan) hanya pada data latih.

### 10.4 Baseline dan Model Utama

| Model | Jenis | Fitur / Arsitektur | Peran |
|---|---|---|---|
| HOG + LBP + histogram warna | Klasik | SVM dan Random Forest | Baseline pembanding |
| MobileNetV2 | CNN transfer learning | Bobot ImageNet | Model utama, ringan |
| EfficientNet-B0 | CNN transfer learning | Bobot ImageNet | Pembanding model utama |
| YOLOv8 | Deteksi objek | Bobot awal dari RDD2022, fine-tune citra lokal | Eksplorasi kelas jalan (opsional) |

### 10.5 Pelatihan
- Dua fase. **Fase 1**: lapisan klasifikasi dilatih dengan lapisan dasar dibekukan, laju belajar 1e-3. **Fase 2**: sebagian lapisan atas dibuka, laju belajar 1e-5.
- Optimizer: Adam. Batch size 32. Maksimum 30 epoch dengan early stopping pada galat validasi.
- Ketidakseimbangan kelas ditangani dengan pembobotan kelas pada fungsi loss dan augmentasi.
- Setiap percobaan dicatat (arsitektur, hiperparameter, hasil) agar dapat direproduksi.

### 10.6 Evaluasi
- Metrik: akurasi, precision, recall, F1-score makro, dan matriks kebingungan.
- Kriteria keberhasilan: F1 makro pada data uji ≥ 0,80 dan lebih tinggi dari baseline.
- Analisis matriks kebingungan untuk pasangan kelas yang sering tertukar, misalnya drainase tersumbat dan permukaan jalan berlumpur.

### 10.7 Tingkat Keparahan (Eksplorasi)
- Kelas jalan dapat dipecah menjadi tiga tingkat keparahan dengan aturan berbasis fitur: rasio luas kotak pembatas terhadap bingkai citra dan jumlah objek terdeteksi.
- Ambang aturan ditetapkan bersama perangkat desa dan divalidasi terhadap label manual.
- Jika waktu tidak mencukupi, cukup klasifikasi tiga tingkat keparahan pada citra utuh.

---

## 11. Alur Pengguna Utama

### 11.1 Alur Warga Melapor
1. Warga membuka WebGIS dari ponsel.
2. Warga memilih "Buat Laporan" dan mengunggah foto.
3. Sistem membaca EXIF. Jika ada koordinat, titik langsung terisi. Jika tidak, sistem meminta izin geolokasi atau meminta warga memilih titik di peta.
4. Warga memilih jenis fasilitas (atau menerima saran AI) dan mengisi deskripsi.
5. Sistem memvalidasi lokasi terhadap batas desa dan memeriksa duplikat.
6. Laporan disimpan dengan status **Menunggu verifikasi**. Klasifikasi AI berjalan di latar belakang.
7. Warga menerima ID laporan dan tautan status.

### 11.2 Alur Pengelola Menangani Laporan
1. Pengelola login dan membuka dasbor.
2. Pengelola melihat daftar prioritas dan peta klaster.
3. Pengelola membuka laporan, memeriksa foto dan prediksi AI, lalu memverifikasi kategori dan menetapkan keparahan.
4. Status diubah ke **Diverifikasi**, lalu **Diproses** saat penanganan dimulai, dan **Selesai** setelah perbaikan.
5. Setiap perubahan tercatat di riwayat status.

### 11.3 Alur Analisis Spasial (Terjadwal atau Saat Diminta)
1. Sistem mengambil laporan aktif (bukan Selesai).
2. Menghitung KDE, DBSCAN, dan Getis-Ord Gi*.
3. Menghitung skor prioritas.
4. Menyimpan hasil ke tabel hasil analisis agar dasbor tidak menghitung ulang setiap kali dibuka.

Catatan: pada tahap awal, analisis dijalankan pada data survei tim dan laporan warga, dengan pemisahan berdasarkan `source_type`.

---

## 12. Spesifikasi API (Flask REST)

Semua respons dalam format JSON. Autentikasi memakai token (misalnya JWT) untuk pengelola dan admin.

| Metode | Endpoint | Akses | Fungsi |
|---|---|---|---|
| POST | `/api/reports` | Publik | Buat laporan baru (termasuk foto, lokasi, kategori) |
| POST | `/api/reports/validate-location` | Publik | Cek apakah koordinat berada di dalam batas desa |
| GET | `/api/reports/{id}/status` | Publik | Cek status dan riwayat ringkas (tanpa data pribadi) |
| GET | `/api/reports` | Pengelola | Daftar laporan dengan filter dan pagination |
| GET | `/api/reports/{id}` | Pengelola | Detail laporan lengkap |
| PATCH | `/api/reports/{id}/status` | Pengelola | Ubah status (validasi alur) |
| PATCH | `/api/reports/{id}/severity` | Pengelola | Tetapkan tingkat keparahan |
| POST | `/api/photos/{id}/predict` | Sistem | Jalankan klasifikasi ulang |
| GET | `/api/map/reports` | Publik | GeoJSON titik laporan publik, dengan filter |
| GET | `/api/map/heatmap` | Pengelola | Grid KDE (GeoJSON atau raster ringan) |
| GET | `/api/map/clusters` | Pengelola | Hasil DBSCAN (GeoJSON) |
| GET | `/api/map/hotspots` | Pengelola | Hasil Getis-Ord Gi* (GeoJSON) |
| GET | `/api/dashboard/summary` | Pengelola | Ringkasan status, jenis, dan tren |
| GET | `/api/dashboard/priorities` | Pengelola | Daftar prioritas dengan skor |
| GET | `/api/admin/parameters` | Admin | Baca parameter analisis |
| PUT | `/api/admin/parameters` | Admin | Ubah parameter analisis |

### 12.1 Contoh Payload Pembuatan Laporan

```json
{
  "facility_type": "PJU",
  "description": "Lampu PJU di depan gang padam sejak tiga hari.",
  "location": { "lat": -7.4742, "lng": 109.3152 },
  "location_source": "device_gps",
  "photo_ids": ["tmp_8f2a..."]
}
```

Koordinat contoh hanya ilustrasi. Pastikan titik uji berada di dalam batas Desa Blater.

### 12.2 Kode Respons Penting
- `201` laporan dibuat
- `400` data tidak lengkap atau format salah
- `422` lokasi di luar batas desa
- `409` laporan duplikat terdeteksi (sertakan ID laporan yang mirip)
- `413` foto melebihi batas ukuran
- `415` format foto tidak didukung
- `401` / `403` autentikasi dan otorisasi

---

## 13. Kebutuhan Non-Fungsional

| Kategori | Kebutuhan |
|---|---|
| Kinerja | Kueri radius dengan indeks GiST harus lebih cepat daripada tanpa indeks pada 100.000 titik sintetis. Halaman peta awal dimuat dalam 3 detik pada koneksi seluler standar (target, bukan jaminan) |
| Responsivitas | Layout berfungsi di ponsel (lebar 360 px ke atas) dan desktop |
| Aksesibilitas | Kontras teks memadai, label formulir jelas, teks alternatif untuk ikon |
| Keamanan | HTTPS, hash kata sandi (bcrypt atau argon2), validasi input server, pembatasan ukuran unggahan (misalnya 5 MB per foto), validasi tipe berkas dengan memeriksa isi, bukan hanya ekstensi |
| Privasi | Data pribadi seminimal mungkin. EXIF dihapus dari versi publik. Wajah dan pelat nomor kendaraan dikaburkan otomatis sebelum publikasi. Identitas pelapor hanya dilihat pengelola |
| Ketersediaan | Purwarupa; tidak ada target SLA, tetapi sistem harus pulih dengan restart layanan |
| Akurasi posisi | RMSE dilaporkan per sumber lokasi (EXIF, geolokasi perangkat, titik manual). Target ≤ 10 m |
| Ketertelusuran | Setiap prediksi AI menyimpan versi model. Setiap perubahan status tercatat |
| Lisensi data | Atribusi OpenStreetMap ditampilkan di peta |
| Kepatuhan | Mengacu pada UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi |

---

## 14. Keamanan dan Pelindungan Data

1. Pengguna diberi pemberitahuan tentang data yang dikumpulkan dan tujuannya sebelum mengirim laporan (checkbox persetujuan).
2. EXIF dihapus dari foto yang ditampilkan publik setelah koordinat diekstraksi.
3. Wajah dan pelat nomor kendaraan dikaburkan secara otomatis pada versi publik, menggunakan model deteksi wajah dan plat nomor sebelum berkas publik disimpan.
4. Identitas pelapor (nama, kontak) hanya dapat dilihat pengelola.
5. Responden kuesioner SUS mengisi secara sukarela dengan persetujuan lisan atau tertulis.
6. Akses ke foto asli dibatasi pada pengelola.

---

## 15. Antarmuka (UI)

### 15.1 Halaman yang Dibutuhkan
1. **Beranda / Peta publik**: peta, layer, filter, tombol "Buat Laporan".
2. **Formulir laporan**: langkah berurutan (foto → lokasi → kategori → deskripsi → kirim).
3. **Konfirmasi laporan**: ID dan tautan status.
4. **Cek status**: masukkan ID, lihat status dan riwayat.
5. **Login pengelola**.
6. **Dasbor pengelola**: ringkasan, daftar prioritas, peta analisis (heatmap, klaster, hotspot), dan filter.
7. **Daftar laporan pengelola**: tabel dengan filter dan pengurutan.
8. **Detail laporan pengelola**: peta kecil, foto, prediksi AI, status, keparahan, riwayat.
9. **Pengaturan admin**: jenis fasilitas, pengguna, parameter analisis.

### 15.2 Prinsip Desain
- Mobile first untuk alur warga. Langkah formulir satu layar per langkah.
- Pelapor selalu tahu di mana posisi titiknya, dengan penanda dan teks alamat atau koordinat.
- Prediksi AI ditampilkan sebagai *saran* dengan persentase confidence, bukan sebagai keputusan.
- Status dan keparahan ditampilkan dengan warna dan label teks, tidak hanya warna.
- Bahasa Indonesia yang sederhana. Hindari istilah GIS teknis di antarmuka warga (misalnya tulis "Titik lokasi" bukan "Geometri Point").

### 15.3 Penanda dan Warna (contoh)
| Elemen | Warna contoh | Bentuk |
|---|---|---|
| Jalan | Oranye | Lingkaran |
| PJU | Kuning | Segitiga |
| Drainase | Biru | Persegi |
| Berat | Merah tua (dengan label "Berat") | Ukuran penanda lebih besar |

---

## 16. Pengujian

### 16.1 Pengujian Model AI
- Evaluasi pada data uji yang tidak dipakai saat pelatihan atau pemilihan hiperparameter.
- Bandingkan SVM/RF, MobileNetV2, dan EfficientNet-B0.
- Laporkan akurasi, precision, recall, F1 makro, matriks kebingungan, dan mAP@0,5 untuk deteksi objek (jika dikerjakan).

### 16.2 Akurasi Posisi
- Minimal 30 titik dengan koordinat GNSS sebagai referensi.
- Hitung RMSE dengan `RMSE = √(Σeᵢ² / n)`, eᵢ = jarak antara koordinat sistem dan koordinat GNSS pada titik ke-i.
- Laporkan terpisah untuk EXIF, geolokasi perangkat, dan titik manual.

### 16.3 Pengujian Fungsional (Black-box)
Skenario inti yang wajib lulus (100%):
1. Unggah foto berkoordinat EXIF di dalam batas desa → titik terisi otomatis, laporan tersimpan.
2. Unggah foto tanpa koordinat, lalu pilih titik manual → laporan tersimpan.
3. Pilih titik di luar batas desa → ditolak dengan pesan jelas (422).
4. Filter berdasarkan kategori dan status → peta dan daftar sesuai.
5. Pengelola mengubah status sesuai alur → riwayat tercatat.
6. Pengelola mencoba melompati status (misalnya ke Selesai langsung) → ditolak.
7. Warga mencoba mengakses endpoint pengelola → ditolak (403).
8. Laporan duplikat dalam 6 meter dan kategori sama → peringatan muncul.
9. Foto melebihi batas ukuran → ditolak (413).
10. Cek status dengan ID valid dan tidak valid.

### 16.4 Kinerja Kueri
- `EXPLAIN ANALYZE` pada kueri radius (`ST_DWithin`) dengan dan tanpa indeks GiST.
- Data sintetis 1.000, 10.000, dan 100.000 titik.
- Laporkan waktu eksekusi (ms) per skala.

### 16.5 Kegunaan (SUS)
- Minimal 20 responden: warga, mahasiswa kost, dan perangkat desa.
- Responden mencoba dua tugas: membuat laporan, dan membaca status penanganan.
- Hitung skor SUS sesuai prosedur baku. Target ≥ 68.

### 16.6 Validasi Lapangan
- Perangkat desa meninjau langsung sejumlah titik prioritas teratas untuk mengonfirmasi hasil analisis spasial.

---

## 17. Rencana Rilis dan Milestone

Dibagi enam tahap, sesuai jadwal laporan.

| Minggu | Tahap | Milestone | Penanggung jawab (dari laporan) |
|---|---|---|---|
| 1–3 | Perencanaan dan akuisisi data spasial | M1: proposal dan desain basis data spasial | Zaki Fatah Alfikri dan tim |
| 4–6 | Pengelolaan dan pra-pemrosesan data | M2: basis data PostGIS terintegrasi dan skrip pra-pemrosesan | Aldi Trio Prabowo |
| 7–10 | Analisis spasial dan pemodelan AI | M3: modul analisis spasial dan model klasifikasi | Satria Megantara Wildan |
| 11–13 | Pengembangan antarmuka WebGIS | M4: purwarupa WebGIS versi alfa | Seluruh anggota |
| 14–15 | Pengujian sistem dan laporan | M5: laporan akhir, repositori GitHub, video demo | Seluruh anggota |
| 16 | Sidang akhir dan demonstrasi | M6: produk siap uji dan presentasi akhir | Seluruh anggota |

### 17.1 Urutan Implementasi yang Disarankan (untuk AI coding)
1. Skema basis data PostGIS dan migrasi (tabel, indeks GiST, data awal `facility_types` dan `report_status`).
2. Impor batas desa dan jaringan jalan, validasi topologi.
3. Endpoint validasi lokasi dan pembuatan laporan (tanpa AI dulu).
4. Ekstraksi EXIF dan penyimpanan foto (versi asli dan publik).
5. Peta publik dengan layer dan penanda.
6. Formulir laporan bertahap.
7. Alur status dan riwayat, serta halaman pengelola.
8. Modul AI: baseline klasik, lalu MobileNetV2, lalu integrasi ke API (dengan layanan terpisah).
9. Analisis spasial: KDE, DBSCAN, Gi*, skor prioritas, dan penyimpanan hasil.
10. Dasbor dan daftar prioritas.
11. Pengujian sesuai bagian 16.

Setiap langkah harus dapat dijalankan dan diuji sendiri sebelum lanjut.

---

## 18. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Jumlah citra lokal terbatas | Model tidak general | Pra-latih pada RDD2022, augmentasi, pembagian data berdasarkan lokasi, dan pengakuan dalam laporan |
| Laporan warga sedikit pada tahap awal | Klaster dan hotspot tidak stabil | Gabungkan dengan data survei tim (dipisah via `source_type`); tandai hasil sebagai indikatif |
| Akurasi EXIF dan GPS ponsel rendah | Titik meleset | Tampilkan akurasi, minta konfirmasi titik di peta, ukur RMSE per sumber |
| DBSCAN sensitif terhadap parameter | Klaster tidak konsisten | Pilih eps dan minPts dengan grafik k-distance dan tinjauan visual |
| KDE tanpa uji signifikansi | Hotspot semu | Gunakan Gi* untuk uji signifikansi, tampilkan hanya yang signifikan |
| Ketidakseimbangan kelas | Model bias | Pembobotan kelas dan augmentasi, pantau F1 makro |
| Layanan Google Fusion Tables sudah dihentikan | Desain lama tidak bisa dipakai | Gunakan PostgreSQL/PostGIS |
| Keterbatasan waktu | Fitur tidak selesai | Fitur C (buffer lanjutan) dapat dicoret tanpa mengganggu inti; rute kunjungan (F-22) sudah ditunda |
| Privasi foto | Data pribadi bocor | EXIF dihapus, wajah dan plat disamarkan, akses foto asli dibatasi |

---

## 19. Keputusan Terbuka (Sudah Diputuskan)

Keputusan berikut sudah disepakati dan menjadi acuan implementasi:

1. **Pelaporan anonim**: warga dapat melapor tanpa akun. Kontak bersifat opsional.
2. **Batas desa**: laporan di luar batas Desa Blater ditolak total dan tidak disimpan.
3. **Framework deep learning**: TensorFlow (Keras).
4. **Pengaburan wajah dan plat nomor**: dilakukan otomatis sebelum versi publik disimpan.
5. **Ambang confidence AI**: 0,85.
6. **Radius laporan duplikat**: 6 meter. Jika 6 meter terlalu dekat dan tidak efektif saat pengujian, gunakan 10 meter.
7. **Rute kunjungan (F-22)**: ditunda ke pengembangan lanjutan, tidak termasuk rilis ini.

---

## 20. Lampiran: Daftar Istilah

| Istilah | Arti |
|---|---|
| WebGIS | Sistem informasi geografis yang diakses lewat peramban web |
| PPGIS | Public Participation GIS, partisipasi warga dalam pemetaan |
| PostGIS | Ekstensi spasial untuk PostgreSQL |
| EPSG:4326 | Sistem koordinat WGS 84 (derajat lintang dan bujur) |
| EPSG:32749 | UTM zona 49S, untuk perhitungan jarak dalam meter |
| EXIF | Metadata foto, termasuk koordinat GPS jika kamera mengaktifkannya |
| KDE | Kernel Density Estimation, peta kepadatan |
| DBSCAN | Algoritma klaster berbasis kepadatan |
| Getis-Ord Gi* | Statistik hotspot dan coldspot lokal |
| RMSE | Root Mean Square Error, galat rata-rata |
| F1 makro | Rata-rata F1 per kelas, memperlakukan semua kelas setara |
| SUS | System Usability Scale, skala kegunaan 0–100 |
| GiST | Indeks spasial di PostgreSQL |
| GNSS | Sistem navigasi satelit global (termasuk GPS) |

---

## 21. Instruksi untuk AI Coding

Gunakan dokumen ini sebagai sumber kebenaran.

- Bangun sesuai urutan di bagian 17.1. Jangan mengerjakan modul AI sebelum alur laporan dasar berjalan.
- Ikuti skema data di bagian 7 persis, termasuk tipe geometri, indeks GiST, dan nilai enum.
- Semua koordinat tersimpan dalam EPSG:4326. Perhitungan jarak dan luas dilakukan dalam EPSG:32749.
- Pisahkan layanan AI sebagai modul sendiri dengan antarmuka `predict(image)`.
- Jangan menyimpan EXIF pada versi foto publik.
- Tulis fungsi validasi lokasi dan deteksi duplikat sebagai fungsi terpisah agar mudah diuji.
- Untuk setiap endpoint, tulis pengujian yang mencakup kasus berhasil dan kasus gagal dari bagian 16.3.
- Jika ada keputusan yang belum jelas (bagian 19), pilih nilai default yang tercantum dan tandai di kode dengan komentar `TODO`.
- Tulis kode, nama tabel, dan nama kolom dalam bahasa Inggris atau bahasa Indonesia secara konsisten. Antarmuka pengguna dalam Bahasa Indonesia.
