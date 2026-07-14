import flet as ft
import pandas as pd
import glob
import os

# --- GÜÇLENDİRİLMİŞ DOSYA ARAMA ---
mevcut_klasor = os.path.dirname(os.path.abspath(__file__))
klasor_yolu = os.path.join(mevcut_klasor, "assets")

# recursive=True ve "**" ekleyerek klasörün içindeki tüm alt klasörleri de taramasını sağladık
arama_deseni = os.path.join(klasor_yolu, "**", "*.csv")
tum_csv_dosyalari = glob.glob(arama_deseni, recursive=True)

if len(tum_csv_dosyalari) == 0:
    print(f"HATA: {klasor_yolu} konumu ve alt klasörlerinde hiçbir CSV bulunamadı!")
    ana_veri_seti = pd.DataFrame() 
else:
    print(f"BAŞARILI: {len(tum_csv_dosyalari)} adet CSV dosyası bulundu.")
    ana_veri_seti = pd.concat([pd.read_csv(d) for d in tum_csv_dosyalari], ignore_index=True)
    ana_veri_seti.columns = ana_veri_seti.columns.str.strip()
    ana_veri_seti['Div'] = ana_veri_seti['Div'].astype(str).str.strip()
    ana_veri_seti['HomeTeam'] = ana_veri_seti['HomeTeam'].astype(str).str.strip()
    ana_veri_seti['AwayTeam'] = ana_veri_seti['AwayTeam'].astype(str).str.strip()
# ---------------------------------------------


# ==========================================
# 2. ANALİZ FONKSİYONU
# ==========================================
def oran_analizi_yap(df, ms1, msx, ms2, ev_takim=None, dep_takim=None, en_yakin_n=20):
    if df.empty:
        return {"hata": "Veri seti bulunamadı. Lütfen klasör yolunu kontrol edin."}

    calisilan_df = df

    # Takım filtresi: iki takımdan herhangi birinin (ev ya da deplasman olarak) yer aldığı maçlar
    if ev_takim or dep_takim:
        takim_maskesi = pd.Series(False, index=calisilan_df.index)
        if ev_takim:
            takim_maskesi |= (calisilan_df['HomeTeam'] == ev_takim) | (calisilan_df['AwayTeam'] == ev_takim)
        if dep_takim:
            takim_maskesi |= (calisilan_df['HomeTeam'] == dep_takim) | (calisilan_df['AwayTeam'] == dep_takim)
        calisilan_df = calisilan_df[takim_maskesi]

    if calisilan_df.empty:
        return {"hata": "Seçilen takım(lar) için hiç geçmiş maç bulunamadı."}

    # Gerekli oran sütunlarında veri olmayan satırları çıkar
    calisilan_df = calisilan_df.dropna(subset=['B365H', 'B365D', 'B365A'])
    if calisilan_df.empty:
        return {"hata": "Seçilen takım(lar) için oran verisi içeren geçmiş maç bulunamadı."}

    # Sabit tolerans yerine: her maçın girilen oranlara olan "uzaklığını" hesapla,
    # en yakın N maçı seç (böylece keyfi tolerans büyütmeye gerek kalmıyor)
    calisilan_df = calisilan_df.copy()
    calisilan_df['_uzaklik'] = (
        (calisilan_df['B365H'] - ms1).abs() +
        (calisilan_df['B365D'] - msx).abs() +
        (calisilan_df['B365A'] - ms2).abs()
    )

    filtrelenmis = calisilan_df.sort_values('_uzaklik').head(en_yakin_n).drop(columns=['_uzaklik']).copy()

    toplam_mac = len(filtrelenmis)
    if toplam_mac == 0:
        return {"hata": "Seçilen takımlar için uygun geçmiş maç bulunamadı."}

    en_uzak_fark = calisilan_df.sort_values('_uzaklik').head(en_yakin_n)['_uzaklik'].max() if '_uzaklik' in calisilan_df.columns else None


    filtrelenmis['2Y_Ev'] = filtrelenmis['FTHG'] - filtrelenmis['HTHG']
    filtrelenmis['2Y_Dep'] = filtrelenmis['FTAG'] - filtrelenmis['HTAG']

    def taraf_sonucu_bul(ev_gol, dep_gol):
        if ev_gol > dep_gol:
            return '1'
        elif ev_gol == dep_gol:
            return 'X'
        else:
            return '2'

    filtrelenmis['IY_Sonucu'] = filtrelenmis.apply(lambda row: taraf_sonucu_bul(row['HTHG'], row['HTAG']), axis=1)
    filtrelenmis['MS_Sonucu'] = filtrelenmis.apply(lambda row: taraf_sonucu_bul(row['FTHG'], row['FTAG']), axis=1)
    filtrelenmis['2Y_Sonucu'] = filtrelenmis.apply(lambda row: taraf_sonucu_bul(row['2Y_Ev'], row['2Y_Dep']), axis=1)

    filtrelenmis['IY_Skor'] = filtrelenmis['HTHG'].astype(int).astype(str) + "-" + filtrelenmis['HTAG'].astype(int).astype(str)
    filtrelenmis['MS_Skor'] = filtrelenmis['FTHG'].astype(int).astype(str) + "-" + filtrelenmis['FTAG'].astype(int).astype(str)
    filtrelenmis['2Y_Skor'] = filtrelenmis['2Y_Ev'].astype(int).astype(str) + "-" + filtrelenmis['2Y_Dep'].astype(int).astype(str)

    filtrelenmis['Ust_25_Durumu'] = (filtrelenmis['FTHG'] + filtrelenmis['FTAG']) > 2.5
    filtrelenmis['KG_Durumu'] = (filtrelenmis['FTHG'] > 0) & (filtrelenmis['FTAG'] > 0)

    iy_ihtimaller = filtrelenmis['IY_Sonucu'].value_counts(normalize=True) * 100
    ms_ihtimaller = filtrelenmis['MS_Sonucu'].value_counts(normalize=True) * 100
    ikinci_yari_ihtimaller = filtrelenmis['2Y_Sonucu'].value_counts(normalize=True) * 100

    iy_skor_ihtimaller = filtrelenmis['IY_Skor'].value_counts(normalize=True) * 100
    ms_skor_ihtimaller = filtrelenmis['MS_Skor'].value_counts(normalize=True) * 100
    ikinci_yari_skor_ihtimaller = filtrelenmis['2Y_Skor'].value_counts(normalize=True) * 100

    ust_yuzdesi = float(filtrelenmis['Ust_25_Durumu'].mean() * 100)
    kg_yuzdesi = float(filtrelenmis['KG_Durumu'].mean() * 100)

    return {
        "Bulunan_Mac_Sayisi": toplam_mac,
        "En_Uzak_Fark": round(float(en_uzak_fark), 3) if en_uzak_fark is not None else None,
        "IY_Ihtimalleri": iy_ihtimaller.round(2).to_dict(),
        "MS_Ihtimalleri": ms_ihtimaller.round(2).to_dict(),
        "2Y_Ihtimalleri": ikinci_yari_ihtimaller.round(2).to_dict(),
        "IY_Skor_Ihtimalleri": iy_skor_ihtimaller.round(2).to_dict(),
        "MS_Skor_Ihtimalleri": ms_skor_ihtimaller.round(2).to_dict(),
        "2Y_Skor_Ihtimalleri": ikinci_yari_skor_ihtimaller.round(2).to_dict(),
        "Ust_2.5_Ihtimali": round(ust_yuzdesi, 2),
        "KG_Var_Ihtimali": round(kg_yuzdesi, 2)
    }


# ==========================================
# 3. FLET İLE KULLANICI ARAYÜZÜ (GUI)
# ==========================================
def main(page: ft.Page):
    page.title = "Kupon Tahmin Uygulaması"
    page.window.width = 420
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = "adaptive"

    baslik = ft.Text("🔥 MAÇ ANALİZ SİSTEMİ", size=24, weight="bold",
                      color=ft.Colors.AMBER_400, text_align="center")

    if not ana_veri_seti.empty and 'Div' in ana_veri_seti.columns:
        lig_listesi = sorted(ana_veri_seti['Div'].dropna().astype(str).unique().tolist())
    else:
        lig_listesi = []

    print(f"DEBUG: {len(lig_listesi)} adet lig bulundu: {lig_listesi}")

    # Takım dropdown'ları önce tanımlanıyor ki lig_secildi fonksiyonu içinden erişilebilsin
    ev_sahibi_dropdown = ft.Dropdown(label="Ev Sahibi Takım", disabled=True, options=[])
    deplasman_dropdown = ft.Dropdown(label="Deplasman Takımı", disabled=True, options=[])

    def lig_secildi(e):
        secilen_lig = lig_dropdown.value
        print(f"DEBUG: on_change tetiklendi. Seçilen lig: {secilen_lig}")

        if not secilen_lig:
            return

        # 1. Veriyi filtrele
        ligin_verisi = ana_veri_seti[ana_veri_seti['Div'].astype(str) == secilen_lig]
        print(f"DEBUG: {secilen_lig} liginde {len(ligin_verisi)} satır maç verisi var.")

        # 2. Takımları ayıkla
        ev = ligin_verisi['HomeTeam'].dropna().astype(str).unique().tolist()
        dep = ligin_verisi['AwayTeam'].dropna().astype(str).unique().tolist()
        takimlar = sorted(set(ev + dep))

        print(f"DEBUG: {secilen_lig} liginde {len(takimlar)} farklı takım bulundu: {takimlar[:5]}...")

        # 3. Yeni options listesini doğrudan ATA — Flet 0.27.x stabil API'si
        ev_sahibi_dropdown.options = [ft.dropdown.Option(t) for t in takimlar]
        deplasman_dropdown.options = [ft.dropdown.Option(t) for t in takimlar]

        ev_sahibi_dropdown.value = None
        deplasman_dropdown.value = None
        ev_sahibi_dropdown.disabled = False
        deplasman_dropdown.disabled = False

        # 4. Kontrolleri tek tek güncelle
        ev_sahibi_dropdown.update()
        deplasman_dropdown.update()
        print("DEBUG: Takım dropdown'ları güncellendi.")

    lig_dropdown = ft.Dropdown(
        label="Lig Seçiniz",
        options=[ft.dropdown.Option(lig) for lig in lig_listesi],
        on_change=lig_secildi
    )

    ms1_input = ft.TextField(label="MS 1", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    msx_input = ft.TextField(label="MS X", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    ms2_input = ft.TextField(label="MS 2", keyboard_type=ft.KeyboardType.NUMBER, expand=True)

    sonuc_ekrani = ft.Column(spacing=10)

    def analiz_et_click(e):
        sonuc_ekrani.controls.clear()
        sonuc_ekrani.update()

        if not lig_dropdown.value or not ev_sahibi_dropdown.value or not deplasman_dropdown.value:
            sonuc_ekrani.controls.append(ft.Text("HATA: Lütfen Lig ve Takımları seçin!", color=ft.Colors.RED_400))
            page.update()
            return

        try:
            ms1_val = float(ms1_input.value.replace(',', '.'))
            msx_val = float(msx_input.value.replace(',', '.'))
            ms2_val = float(ms2_input.value.replace(',', '.'))
        except (ValueError, AttributeError):
            sonuc_ekrani.controls.append(ft.Text("HATA: Lütfen oranları sayı olarak girin!", color=ft.Colors.RED_400))
            page.update()
            return

        print(f"DEBUG: Yeni sorgu -> Lig:{lig_dropdown.value} Ev:{ev_sahibi_dropdown.value} "
              f"Dep:{deplasman_dropdown.value} | MS1:{ms1_val} MSX:{msx_val} MS2:{ms2_val}")

        sonuc = oran_analizi_yap(
            ana_veri_seti, ms1_val, msx_val, ms2_val,
            ev_takim=ev_sahibi_dropdown.value,
            dep_takim=deplasman_dropdown.value,
            en_yakin_n=20
        )

        print(f"DEBUG: Bu sorgu için bulunan sonuç -> {sonuc.get('Bulunan_Mac_Sayisi', sonuc.get('hata'))}")

        if "hata" in sonuc:
            sonuc_ekrani.controls.append(ft.Text(sonuc["hata"], color=ft.Colors.RED_400))
        else:
            sonuc_ekrani.controls.extend([
                ft.Text(f"✅ En yakın {sonuc['Bulunan_Mac_Sayisi']} maç bulundu ve analiz edildi.",
                        color=ft.Colors.GREEN_400, weight="bold", size=16),
                ft.Divider(),
                ft.Text(f"⚽ 2.5 ÜST İhtimali: % {sonuc['Ust_2.5_Ihtimali']}", size=15),
                ft.Text(f"🤝 KG VAR İhtimali: % {sonuc['KG_Var_Ihtimali']}", size=15),
                ft.Divider(),
                ft.Text("--- TARAF OLASILIKLARI ---", color=ft.Colors.BLUE_200, weight="bold"),
                ft.Text(f"Maç Sonu : {sonuc['MS_Ihtimalleri']}"),
                ft.Text(f"İlk Yarı : {sonuc['IY_Ihtimalleri']}"),
                ft.Text(f"2. Yarı  : {sonuc['2Y_Ihtimalleri']}"),
                ft.Divider(),
                ft.Text("--- DETAYLI SKOR TAHMİNLERİ ---", color=ft.Colors.BLUE_200, weight="bold"),
                ft.Text(f"MS Skorları : {sonuc['MS_Skor_Ihtimalleri']}"),
                ft.Text(f"İY Skorları : {sonuc['IY_Skor_Ihtimalleri']}")
            ])

        page.update()

    hesapla_btn = ft.ElevatedButton(
        "Analiz Et", on_click=analiz_et_click, width=400, height=45,
        style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_700, color=ft.Colors.BLACK)
    )

    page.add(
        ft.Column(
            [
                baslik,
                ft.Divider(),
                lig_dropdown,
                ev_sahibi_dropdown,
                deplasman_dropdown,
                ft.Row([ms1_input, msx_input, ms2_input], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                hesapla_btn,
                ft.Divider(),
                sonuc_ekrani
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )


ft.app(target=main)