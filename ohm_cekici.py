# -*- coding: utf-8 -*-
"""
Ohm'un Çekici v4 - 18650'li DIY elektrikli tornavida (GW Finesse remix, CC0 / Public Domain)
v2: kilit emniyet switch'i (kilitliyken motor çalışmaz), eyer tipi rocker + koruma rayları
v3: yukarıdan-aşağı montaj: her şey alt yarıya düşer, rocker en son dışarıdan tık diye takılır
Parametrik CadQuery modeli.

Koordinatlar (mm):  Z = tornavida ekseni (uç +Z yönünde, gövde ön yüzü z=0)
                     Y = yukarı (rocker / buton tarafı +Y), X = yan
Gövde y=0 düzleminden ikiye bölünür: UST (rocker + yazı) ve ALT (kilit sürgüsü).

Çalıştırma:  python3 ohm_cekici.py   ->  out/ klasörüne STL + STEP yazar
"""
import os, math
import cadquery as cq

# ---------------------------------------------------------------- PARAMETRELER
R_OUT = 12.75          # gövde dış yarıçapı (25.5 mm çap)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TEXT = "OHM'UN ÇEKİCİ"

# N20 motor (12 x 10 kesit)
MOT_W, MOT_H = 12.0, 10.0
MOT_TOL = 0.15
Z_FRONT_WALL = 4.0     # ön duvar kalınlığı
Z_MOT_END = 29.5       # motor cebinin arka ucu (z = -29.5)

# Mil / kilit yakası
SPIGOT_R, SPIGOT_BORE_R, SPIGOT_DEPTH = 5.0, 5.25, 2.5
COLLAR_R, COLLAR_Z0, COLLAR_Z1 = 8.0, 0.25, 5.25
GROOVE_W, GROOVE_FLOOR_R, N_GROOVES = 4.4, 5.0, 4
NOSE_R, NOSE_TOP = 5.5, 17.0
HEX_AF = 4.05          # H4 hassas uç (4 mm altıgen) – sıkı geçme
HEX_DEPTH = 10.0
DSHAFT_R, DSHAFT_FLAT = 1.6, 1.2

# Kilit sürgüsü (alt)
SL_W, SL_Y0, SL_Y1 = 7.0, -8.35, -5.25       # geniş gövde
SL_LEN = 10.0
TONGUE_W = 4.0
TRAVEL = 6.2          # 1. mm'de güç kesilir, dil yakaya 1.8. mm'de değer
STEM_W = 2.4
CH_CLR = 0.15

# Pil yatağı (18650)
BAT_R = 9.5            # 19.0 mm delik
Z_BULK1 = (42.5, 45.0)         # ön bölme (emniyet switch'inin arkası)
BAY_LEN = 72.0                 # 65-69 mm pil + yay
Z_BAY = (45.0, 45.0 + BAY_LEN)  # -45 .. -117
BULK2_LEN = 8.5
CONTACT_W, CONTACT_H, CONTACT_T = 13.2, 15.6, 0.9

# TP4056 bölmesi
# TP4056 3.7V Mini Şarj Devresi - Korumalı Mod Type-C (Robo90 R005486), 18 x 14 mm
TP_BOARD_W, TP_BOARD_LEN = 14.0, 17.0   # kart (PCB) eni ve boyu; USB-C dahil toplam 18 mm
USB_OVER = 2.5                  # USB-C'nin kart kenarından taşması (fotoğraftan ölçüldü)
USB_XOFF = 0.0                  # USB-C kartın ortasında (fotoğraftan ölçüldü)
TP_LEN = USB_OVER + TP_BOARD_LEN + 0.15 + 1.5 + 4.5   # kart + dayanak + kablo payı
TP_Y0 = -1.6                    # kart alt yüzü (1.0-1.6 mm kart kalınlıklarına uyar)
CH_R = 9.6
END_WALL = 3.0
USB_W, USB_H, USB_Y = 9.6, 4.4, 1.33

# Rocker / switch yığını (y)
SW_L, SW_W, SW_H = 12.8, 5.8, 6.5     # mini mikro switch gövdesi
Y_SLED0, Y_SLED1 = 5.05, 7.7          # kızak motorun üstüne oturur; altında kablo olukları
Y_SW_TOP = Y_SLED1 + SW_H              # 13.2
Y_ROCK_BOT, Y_SHELL_IN, Y_HUMP_TOP = Y_SW_TOP + 1.0, Y_SW_TOP + 2.6, Y_SW_TOP + 4.6   # rocker alt yüzü düz
ROCK_RIM = 0.6          # rocker kenarı gövde üstünden yükseklik
ROCK_RIDGE = 1.6        # orta (pivot) sırtı tepe yüksekliği
RAIL_H = 1.1            # koruma rayları yüksekliği (kenardan 0.5 yukarıda)
DISH_R, DISH_D, DISH_OFF = 18.0, 0.6, 8.5   # parmak çanakları
SLED_Z0 = -35.25

# Kilit emniyet switch'i (mini mikro switch, uzun paletli; palet öne bakar)
ISW_Z = -34.0            # palet yüzü (switch ön yüzü)
ISW_Y0, ISW_Y1 = -8.6, -2.8
ISW_PRESS = 1.0          # kilit açıkken kuyruk ucu paleti bu kadar içeri iter
TAIL_W = 3.6
ZC = -19.0                              # rocker pivot z
ROCK_HALF_L, ROCK_HALF_W = 15.0, 5.0
HUMP_W = 8.5

Z_BAY0, Z_BAY1 = -Z_BAY[0], -Z_BAY[1]
Z_B2_1 = Z_BAY1 - BULK2_LEN
Z_TP1 = Z_B2_1 - TP_LEN
Z_END = Z_TP1 - END_WALL
BODY_LEN = -Z_END

# ---------------------------------------------------------------- yardımcılar
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cylz(r, z0, z1, x=0, y=0):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((x, y, z0))

def cyly(r, y0, y1, x=0, z=0):
    return cq.Workplane("XZ").circle(r).extrude(-(y1 - y0)).translate((x, y0, z))

def cylx(r, x0, x1, y=0, z=0):
    return cq.Workplane("YZ").circle(r).extrude(x1 - x0).translate((x0, y, z))

def hump_section(top, w=HUMP_W, r=3.0):
    """Alt kenarı y=0'da, üst köşeleri yuvarlatılmış dikdörtgen tel (XY düzleminde)."""
    c = r * math.cos(math.pi / 4)
    return [(-w, 0), (w, 0), (w, top - r), ((w - r) + c, top - r + c), (w - r, top),
            (-(w - r), top), (-(w - r) - c, top - r + c), (-w, top - r)]

def hump_solid():
    def wire_at(top, z):
        p = hump_section(top)
        wp = cq.Workplane("XY").workplane(offset=z)
        return (wp.moveTo(*p[0]).lineTo(*p[1]).lineTo(*p[2]).threePointArc(p[3], p[4])
                  .lineTo(*p[5]).threePointArc(p[6], p[7]).close())
    main = wire_at(Y_HUMP_TOP, -37.0).extrude(37.0)
    # arkaya doğru yumuşak rampa
    p_hi, p_lo = hump_section(Y_HUMP_TOP), hump_section(10.5, w=6.5, r=2.5)
    ramp = (cq.Workplane("XY").workplane(offset=-37.0)
            .moveTo(*p_hi[0]).lineTo(*p_hi[1]).lineTo(*p_hi[2]).threePointArc(p_hi[3], p_hi[4])
            .lineTo(*p_hi[5]).threePointArc(p_hi[6], p_hi[7]).close()
            .workplane(offset=-11.0)
            .moveTo(*p_lo[0]).lineTo(*p_lo[1]).lineTo(*p_lo[2]).threePointArc(p_lo[3], p_lo[4])
            .lineTo(*p_lo[5]).threePointArc(p_lo[6], p_lo[7]).close()
            .loft(ruled=False))
    return main.union(ramp)

# ---------------------------------------------------------------- GÖVDE (tek parça, sonra bölünür)
def build_body():
    body = cylz(R_OUT, Z_END, 0).union(hump_solid())
    # rocker koruma rayları: avuç düz basınca rocker'ın uçlarına değmez
    wl = ROCK_HALF_L + 0.35
    for sgn in (-1, 1):
        rz0, rz1 = ZC - wl - 1.2, ZC + wl + 1.2
        rail = box(-0.8, 0.8, Y_HUMP_TOP - 2.0, Y_HUMP_TOP + RAIL_H - 0.8, rz0, rz1).union(
            cylz(0.8, rz0, rz1, y=Y_HUMP_TOP + RAIL_H - 0.8))
        body = body.union(rail.translate((sgn * (ROCK_HALF_W + 0.3 + 0.85), 0, 0)))
    # ön ve arka kenar yuvarlatma
    try:
        body = body.faces("<Z").edges().fillet(1.6)
    except Exception:
        pass
    # sürgü pedi için alt düzlük
    body = body.cut(box(-8, 8, -20, -12.3, -22.0, 1))

    # --- ön duvar: mil yatağı + redüktör çıkıntısı deliği
    body = body.cut(cylz(SPIGOT_BORE_R, -SPIGOT_DEPTH, 0.1))
    body = body.cut(cylz(2.4, -Z_FRONT_WALL - 0.1, 0.1))
    # --- motor cebi
    mw, mh = MOT_W / 2 + MOT_TOL, MOT_H / 2 + MOT_TOL
    body = body.cut(box(-mw, mw, -mh, mh, -Z_MOT_END, -Z_FRONT_WALL))
    # motor arka tutucu dudak (ortası açık: terminaller; altı açık: sürgü kuyruğu dikey iner)
    body = body.cut(box(-4.0, 4.0, -3.2, 3.2, -Z_MOT_END - 1.2, -Z_MOT_END + 0.1))
    body = body.cut(box(-TAIL_W / 2 - 0.2, TAIL_W / 2 + 0.2, -5.3, -3.1, -Z_MOT_END - 1.2, -Z_MOT_END + 0.1))
    # --- kablo boşluğu (motor arkası): önde tam, arkada switch'in üstü
    wcav = cylz(BAT_R, -Z_BULK1[0], -Z_MOT_END - 1.0).cut(box(-20, 20, -20, ISW_Y1 + 0.4, -60, ISW_Z))
    body = body.cut(wcav)
    # --- kilit emniyet switch'i cebi (alt yarı) + bacak boşluğu
    body = body.cut(box(-SW_L / 2 - 0.15, SW_L / 2 + 0.15, ISW_Y0 - 0.15, ISW_Y1 + 0.5,
                        ISW_Z - SW_H - 0.15, ISW_Z + 0.6))
    body = body.cut(box(-5.0, 5.0, ISW_Y0 + 0.6, ISW_Y1 + 0.5, -Z_BULK1[0] - 0.5, ISW_Z - SW_H))
    # --- üst: rocker/switch boşluğu
    body = body.cut(box(-6.8, 6.8, 0, Y_SLED1, SLED_Z0 - 0.3, -Z_FRONT_WALL))           # kızak katı
    body = body.cut(box(-5.4, 5.4, 0, Y_SHELL_IN, SLED_Z0 - 0.3, -Z_FRONT_WALL))        # switch hacmi
    body = body.cut(box(-6.5, 6.5, 0, Y_SHELL_IN, ZC - 2.6, ZC + 2.6))                # rocker tırnak geçişi
    wl, ww = ROCK_HALF_L + 0.35, ROCK_HALF_W + 0.3
    body = body.cut(box(-ww, ww, 0, Y_HUMP_TOP + 2, ZC - wl, ZC + wl))               # rocker penceresi
    # --- alt: kilit sürgüsü kanalı
    sw = SL_W / 2 + CH_CLR
    ch_z0 = -Z_FRONT_WALL - SL_LEN - TRAVEL - 0.1
    body = body.cut(box(-sw, sw, SL_Y0 - CH_CLR, -mh + 0.01, ch_z0, -Z_FRONT_WALL))
    # kuyruk kanalı (motorun altından emniyet switch'ine)
    body = body.cut(box(-TAIL_W / 2 - 0.2, TAIL_W / 2 + 0.2, SL_Y0 - CH_CLR, -mh + 0.01, ISW_Z - 0.01, ch_z0 + 0.01))
    tw = TONGUE_W / 2 + 0.1
    body = body.cut(box(-tw, tw, SL_Y0 - CH_CLR, 0.01, -Z_FRONT_WALL - 0.1, 0.1))  # dil yuvası: yukarı açık -> sürgü dikey bırakılır
    # sap yarığı (dışarı)
    sh = STEM_W / 2 + 0.15
    st_front = -Z_FRONT_WALL - 2.5 + 0.2
    st_back = -Z_FRONT_WALL - TRAVEL - 2.5 - 5.0 - 0.2
    body = body.cut(box(-sh, sh, -20, SL_Y0, st_back, st_front))
    # detent çentikleri (kanal yan duvarı, +X)
    for zz in (-Z_FRONT_WALL - TRAVEL - 2.5, -Z_FRONT_WALL - 2.5):
        body = body.cut(cyly(0.5, SL_Y0 - CH_CLR, -mh, x=sw, z=zz))

    # --- ön bölme + kontak cebi + M3 (pul+vida alternatifi)
    body = body.cut(box(-CONTACT_W / 2, CONTACT_W / 2, -CONTACT_H / 2, CONTACT_H / 2,
                        Z_BAY0, Z_BAY0 + CONTACT_T))
    body = body.cut(cylz(1.65, Z_BAY0, -Z_BULK1[0] + 0.1))
    # --- pil yatağı
    body = body.cut(cylz(BAT_R, Z_BAY1, Z_BAY0))
    # --- arka bölme: kontak cebi + yay oturağı
    body = body.cut(box(-CONTACT_W / 2, CONTACT_W / 2, -CONTACT_H / 2, CONTACT_H / 2,
                        Z_BAY1 - CONTACT_T, Z_BAY1))
    body = body.cut(cylz(4.2, Z_BAY1 - 2.5, Z_BAY1))
    # --- TP4056 bölmesi
    body = body.cut(cylz(CH_R, Z_TP1, Z_B2_1))
    # USB-C: fiş gövdesi için dış girinti + 1.2 mm yüz duvarı içinde port deliği
    rec = (cq.Workplane("XY").rect(12.8, 7.2).extrude(END_WALL - 1.2 + 0.5)
           .edges("|Z").fillet(2.4).translate((USB_XOFF, USB_Y, Z_END - 0.5)))
    body = body.cut(rec)
    port = (cq.Workplane("XY").rect(USB_W, USB_H).extrude(1.6)
            .edges("|Z").fillet(1.4).translate((USB_XOFF, USB_Y, Z_TP1 - 1.4)))
    body = body.cut(port)
    # şarj LED penceresi (üst): LED'ler USB-C'nin sağında, kartın ön kısmında
    body = body.cut(box(3.0, 6.5, 4, 20, Z_TP1 + USB_OVER + 7.5, Z_TP1 + USB_OVER + 11.5))
    # --- TP4056 mini: oturak rayları + yan kılavuzlar + arka dayanak (alt yarı)
    # Fiş takılırken kart içeri itilir: arka kenarı dayanak bloklarına yaslanır, kayamaz.
    zb0 = Z_TP1 + USB_OVER
    zrear = zb0 + TP_BOARD_LEN
    hw = TP_BOARD_W / 2
    for sg in (-1, 1):
        def bx(a0, a1, y0, y1, z0, z1):
            x0, x1 = sorted((sg * a0, sg * a1)); return box(x0, x1, y0, y1, z0, z1)
        body = body.union(bx(hw - 2.2, hw + 0.6, -3.5, TP_Y0, zb0, zrear + 0.01))          # oturak
        body = body.union(bx(hw + 0.15, hw + 1.3, -3.5, 0.0, zb0, zrear + 0.01))            # yan kılavuz
        body = body.union(bx(hw - 3.5, hw + 0.6, -3.5, TP_Y0 + 0.9, zrear + 0.15, zrear + 1.65))  # dayanak
    # --- kablo kanalı (sol yan, ayırma düzleminde; 3 ince kablo)
    body = body.cut(box(-11.1, -8.9, -3.0, 0.0, Z_B2_1 - 0.5, -Z_MOT_END - 1.0))
    # --- tutuş oluğu (pil bölgesi)
    for ang in (25, 55, 125, 155, -30, -60, -90, -120, -150):
        a = math.radians(ang)
        x, y = (R_OUT + 0.35) * math.cos(a), (R_OUT + 0.35) * math.sin(a)
        body = body.cut(cylz(0.95, -112, -55, x=x, y=y))
    return body


def text_cut():
    """Üst yüzeye kazınacak yazı katısı."""
    t = (cq.Workplane("XY")
         .text(TEXT, 6.2, 3.0, font="DejaVu Sans", fontPath=FONT, kind="bold",
               halign="center", valign="center"))
    # XY'de yazılmış metni: taban çizgisi +Z, harf yukarısı +X olacak şekilde döndür
    t = t.rotate((0, 0, 0), (0, 0, 1), -90)     # taban çizgisi -Y, harf üstü +X
    t = t.rotate((0, 0, 0), (1, 0, 0), -90)     # taban çizgisi +Z, kalınlık +Y
    bb = t.val().BoundingBox()
    # derinlik: tepe noktada 0.9 mm
    t = t.translate((-(bb.xmin + bb.xmax) / 2, (R_OUT - 0.9) - bb.ymin, -83.0 - (bb.zmin + bb.zmax) / 2))
    return t


def engrave(body):
    """Harfleri tek tek kes (bileşik kesimde Ç kayboluyordu)."""
    for sol in text_cut().val().Solids():
        body = body.cut(cq.Workplane("XY").add(sol))
    return body


PIN_X = 10.0
PINS = [(PIN_X, -9.0), (-PIN_X, -9.0), (PIN_X, -25.0), (-PIN_X, -25.0)]   # z konumları sonra eklenir


def pin_positions():
    return PINS + [(PIN_X, Z_TP1 + 10.0), (-PIN_X, Z_TP1 + 10.0)]


def split(body):
    """Gövdeyi ikiye böler. Vida yok: 6 baskı pim (alttan takılır, üstte tık diye kilitlenir)."""
    top = body.intersect(box(-30, 30, 0, 40, Z_END - 5, 30))
    bot = body.intersect(box(-30, 30, -40, 0, Z_END - 5, 30))
    for (x, z) in pin_positions():
        top = top.cut(box(x - 1.15, x + 1.15, -0.1, 3.4, z - 1.6, z + 1.6))                 # kare delik
        x0, x1 = sorted((x - math.copysign(1.4, x), x + math.copysign(4.0, x)))
        top = top.cut(box(x0, x1, 3.4, 5.8, z - 2.5, z + 2.5))                                # diş cebi (yandan açık)
        bot = bot.cut(box(x - 1.15, x + 1.15, -30, 0.1, z - 1.6, z + 1.6))
        bot = bot.cut(box(x - 1.15, x + 1.15, -30, -5.0, z - 3.2, z + 3.2))                # başlık cebi
    return top, bot


def build_pin(x=PIN_X, z=0.0):
    """Tırnaklı pim. Düz yatırarak basılır (2 mm kalınlık tabla yönünde)."""
    p = box(x - 1.0, x + 1.0, -7.0, -5.0, z - 2.9, z + 2.9)                    # başlık
    p = p.union(box(x - 1.0, x + 1.0, -5.01, -4.0, z - 1.5, z + 1.5))          # gövde
    for sg in (-1, 1):
        a, b = sorted((sg * 0.7, sg * 1.5))
        p = p.union(box(x - 1.0, x + 1.0, -4.01, 3.41, z + a, z + b))         # bacak (0.8)
        prof = [(0.7, 3.4), (2.2, 3.4), (2.2, 4.1), (1.5, 5.4), (0.7, 5.4)]     # diş: alt yüz düz, üst pah
        prof = [(z + sg * zz, y) for (zz, y) in prof]
        barb = (cq.Workplane("YZ").polyline([(y, zz) for (zz, y) in prof]).close()
                .extrude(2.0).translate((x - 1.0, 0, 0)))
        p = p.union(barb)
    return p


# ---------------------------------------------------------------- AYRI PARÇALAR
def build_shaft():
    s = cylz(SPIGOT_R, -SPIGOT_DEPTH + 0.1, COLLAR_Z0 + 0.01)
    collar = cylz(COLLAR_R, COLLAR_Z0, COLLAR_Z1)
    for i in range(N_GROOVES):
        g = box(-GROOVE_W / 2, GROOVE_W / 2, -COLLAR_R - 1, -GROOVE_FLOOR_R, COLLAR_Z0 - 0.1, COLLAR_Z1 + 0.1)
        collar = collar.cut(g.rotate((0, 0, 0), (0, 0, 1), 360 / N_GROOVES * i))
    # yakanın önü 45° koni: uç aşağı basılırken desteksiz çıkar
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(COLLAR_R, NOSE_R, COLLAR_R - NOSE_R,
                                                    cq.Vector(0, 0, COLLAR_Z1 - 0.01), cq.Vector(0, 0, 1)))
    collar = collar.union(cone)
    nose = cylz(NOSE_R, COLLAR_Z1 - 0.01, NOSE_TOP)
    try:
        nose = nose.faces(">Z").edges().chamfer(0.8)
    except Exception:
        pass
    s = s.union(collar).union(nose)
    # D mil deliği
    d = cylz(DSHAFT_R, -SPIGOT_DEPTH, 6.0).intersect(box(-DSHAFT_FLAT, 5, -5, 5, -SPIGOT_DEPTH - 1, 7))
    s = s.cut(d)
    # altıgen uç yuvası
    hx = (cq.Workplane("XY").polygon(6, HEX_AF / math.cos(math.pi / 6)).extrude(HEX_DEPTH + 1)
          .translate((0, 0, NOSE_TOP - HEX_DEPTH)))
    s = s.cut(hx)
    return s


def build_rocker():
    """Eyer tipi rocker: iki içbükey parmak çanağı + ortada pivot sırtı.
    Ön çanakta 1 ok (sık), arka çanakta 2 ok (gevşet). Alt yüz düz -> dik basılır, destek yok."""
    yrim = Y_HUMP_TOP + ROCK_RIM
    r = box(-ROCK_HALF_W, ROCK_HALF_W, Y_ROCK_BOT, yrim, ZC - ROCK_HALF_L, ZC + ROCK_HALF_L)
    try:
        r = r.edges("|Y").fillet(2.0)
    except Exception:
        pass
    # orta sırt (pivot hattı): dokunsal ayırıcı, avuç buraya değer -> rocker devrilmez
    ridge = cylx(1.6, -ROCK_HALF_W + 0.4, ROCK_HALF_W - 0.4, y=Y_HUMP_TOP + ROCK_RIDGE - 1.6, z=ZC)
    r = r.union(ridge.intersect(box(-6, 6, yrim - 0.5, 40, ZC - 3, ZC + 3)))
    # parmak çanakları
    for dz in (+DISH_OFF, -DISH_OFF):
        sph = cq.Workplane("XY").sphere(DISH_R).translate((0, yrim - DISH_D + DISH_R, ZC + dz))
        r = r.cut(sph)
    try:
        r = r.faces(">Y[-2]").edges().fillet(0.3)
    except Exception:
        pass
    # uç alt rahatlatması (switch gövdesine çarpmasın), 45° pah -> desteksiz basılır
    for sgn in (-1, 1):
        rel = (cq.Workplane("YZ").polyline([(Y_ROCK_BOT - 1, 11.0), (Y_ROCK_BOT + 0.7, 11.7),
                                             (Y_ROCK_BOT + 0.7, 16), (Y_ROCK_BOT - 1, 16)]).close()
               .extrude(14).translate((-7, 0, 0)))
        if sgn < 0:
            rel = rel.mirror("XY")
        r = r.cut(rel.translate((0, 0, ZC)))
    # tık-takma kancaları: rocker gövde kapandıktan sonra dışarıdan bastırılarak takılır
    yb0, yb1 = Y_ROCK_BOT, Y_SHELL_IN - 0.05
    for s in (-1, 1):
        zf = ZC + s * 7.0                       # sabit uç (bir taraf önde, diğeri arkada)
        zfree = ZC - s * 1.6                    # serbest uç
        za, zb = min(zf, zfree), max(zf, zfree)
        xin, xout = 3.65, ROCK_HALF_W      # kiriş 0.85 mm (2 çizgi)
        # kirişi gövdeden ayıran yarık (iç yan + üst + serbest uç)
        r = r.cut(box(min(s * xin, s * (xin + 0.5)), max(s * xin, s * (xin + 0.5)), yb0 - 0.1, yb1 + 0.45, za - 0.01, zb + 0.01))  # 0.5 yarık
        r = r.cut(box(min(s * xin, s * (xout + 0.1)), max(s * xin, s * (xout + 0.1)), yb1, yb1 + 0.45, za - 0.01, zb + 0.01))
        zcut = zfree - s * 0.5
        r = r.cut(box(min(s * xin, s * (xout + 0.1)), max(s * xin, s * (xout + 0.1)), yb0 - 0.1, yb1 + 0.45,
                      min(zfree, zcut), max(zfree, zcut)))
        # kanca (alt dış köşesi 45° pahlı -> içeri kayar, üst yüzü kabuğun altına oturur)
        hz0, hz1 = (zfree, zfree + s * 2.6) if s > 0 else (zfree + s * 2.6, zfree)
        hz0, hz1 = min(hz0, hz1), max(hz0, hz1)
        prof = [(xout - 0.01, yb0), (xout - 0.01, yb1), (xout + 0.75, yb1), (xout + 0.75, yb1 - 0.75)]
        prof = [(s * x, y) for (x, y) in prof]
        hook = cq.Workplane("XY").polyline(prof).close().extrude(hz1 - hz0).translate((0, 0, hz0))
        r = r.union(hook)
    # dokunsal oklar (çanak dibinden 0.5 mm kazıma)
    yb = yrim - DISH_D - 0.5
    def chevron(zt, direction):
        c = None
        for side in (-1, 1):
            bar = box(-0.65, 0.65, yb, yb + 3, -1.8, 1.8)
            bar = bar.rotate((0, 0, 0), (0, 1, 0), -side * direction * 50).translate((side * 1.35, 0, zt))
            c = bar if c is None else c.union(bar)
        return c
    r = r.cut(chevron(ZC + DISH_OFF, +1))
    r = r.cut(chevron(ZC - DISH_OFF + 1.7, -1)).cut(chevron(ZC - DISH_OFF - 1.7, -1))
    return r


def build_sled():
    """Switch kızağı: motorun üstüne oturur, iki mikro switch + pivot sırtı."""
    z0, z1 = SLED_Z0, -Z_FRONT_WALL - 0.25
    s = box(-6.6, 6.6, Y_SLED0, Y_SLED1, z0, z1)
    try:
        s = s.faces(">Y").edges("|Z").chamfer(0.6)    # kapanırken üst yarıya kendiliğinden ortalanır
    except Exception:
        pass
    sw_in = SW_W / 2 + 0.15
    wall_top = Y_SLED1 + 3.8
    pockets = [(-5.0, -18.1), (-19.9, -33.0)]
    for (a, b) in pockets:
        s = s.union(box(-sw_in - 0.9, sw_in + 0.9, Y_SLED1 - 0.01, wall_top, b - 0.8, a + 0.8))
    for (a, b) in pockets:
        s = s.cut(box(-sw_in, sw_in, Y_SLED1, wall_top + 1, b, a))
        # bacak/kablo geçişi (taban boşluğu) – switch kenar rayların üstüne oturur
        s = s.cut(box(-2.2, 2.2, Y_SLED0 - 1, Y_SLED1 + 0.1, b + 0.6, a - 0.6))
    # alt yüz kablo olukları: switch bacaklarından arkaya (kablo boşluğuna)
    for gx in (-1.7, 1.7):
        s = s.cut(box(gx - 0.75, gx + 0.75, Y_SLED0 - 0.1, Y_SLED0 + 1.4, z0 - 0.1, -5.6))
    # pivot bloğu + sırt
    s = s.union(box(-3.8, 3.8, Y_SLED1 - 0.01, Y_ROCK_BOT - 0.8, -19.9, -18.1))
    s = s.union(cylx(0.8, -3.8, 3.8, y=Y_ROCK_BOT - 0.8, z=ZC))
    return s


def build_slider():
    """Kilit sürgüsü (gergi parmağı detentli). Konum: kilit AÇIK (geri)."""
    shoulder = -Z_FRONT_WALL - TRAVEL
    w = SL_W / 2
    s = box(-w, w, SL_Y0, SL_Y1, shoulder - SL_LEN, shoulder)
    tongue_len = Z_FRONT_WALL + COLLAR_Z1 - 0.6   # kilitliyken uç yakanın içinde, burnu ezmez
    s = s.union(box(-TONGUE_W / 2, TONGUE_W / 2, SL_Y0 + 0.05, SL_Y1, shoulder - 0.01, shoulder + tongue_len))
    try:
        s = s.faces(">Z").edges("|X").chamfer(0.6)
    except Exception:
        pass
    # sap + pim (ped için)
    st0, st1 = shoulder - 2.5 - 5.0, shoulder - 2.5
    s = s.union(box(-STEM_W / 2, STEM_W / 2, -12.45, SL_Y0 + 0.01, st0, st1))
    s = s.union(box(-1.0, 1.0, -13.55, -12.4, st0 + 1.5, st1 - 1.5))
    # emniyet switch'i kuyruğu (motorun altından geçer)
    tail_tip = ISW_Z + 2.0 - ISW_PRESS          # palet ~2 mm açık durur varsayımı
    s = s.union(box(-TAIL_W / 2, TAIL_W / 2, SL_Y0 + 0.1, SL_Y1, tail_tip, shoulder - SL_LEN + 0.01))
    # detent parmağı (+X kenarı)
    s = s.cut(box(w - 1.4, w - 0.9, SL_Y0 - 1, SL_Y1 + 1, shoulder - 9.0, shoulder - 1.0))
    s = s.cut(box(w - 1.4, w + 1, SL_Y0 - 1, SL_Y1 + 1, shoulder - 1.5, shoulder - 1.0))
    s = s.union(cyly(0.4, SL_Y0, SL_Y1, x=w - 0.05, z=shoulder - 2.5))
    return s


def build_pad():
    shoulder = -Z_FRONT_WALL - TRAVEL
    st0, st1 = shoulder - 2.5 - 5.0, shoulder - 2.5
    zc = (st0 + st1) / 2
    p = box(-5.0, 5.0, -15.0, -12.55, zc - 6.0, zc + 6.0)
    try:
        p = p.edges("|Y").fillet(2.5).faces("<Y").edges().fillet(0.8)
    except Exception:
        pass
    p = p.cut(box(-1.1, 1.1, -13.7, -12.0, st0 + 1.4, st1 - 1.4))  # pim deliği
    for k in range(-2, 3):   # kaymaz kanallar
        p = p.cut(cylx(0.45, -6, 6, y=-15.05, z=zc + k * 2.2))
    return p


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out, exist_ok=True)
    body = engrave(build_body())
    top, bot = split(body)
    parts = {
        "ohm_govde_ust": top, "ohm_govde_alt": bot, "ohm_mil": build_shaft(),
        "ohm_rocker": build_rocker(), "ohm_switch_kizak": build_sled(),
        "ohm_kilit_surgu": build_slider(), "ohm_kilit_ped": build_pad(),
        "ohm_pim": build_pin(0.0, 0.0),
    }
    for n, p in parts.items():
        cq.exporters.export(p, os.path.join(out, n + ".stl"), tolerance=0.02, angularTolerance=0.15)
        cq.exporters.export(p, os.path.join(out, n + ".step"))
        print(n, "ok")
    print("BODY_LEN", BODY_LEN)
