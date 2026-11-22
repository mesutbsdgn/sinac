"""Testler için yalnız standart kütüphaneyle tek sayfalı PDF üretir (Type1 çekirdek yazı tipleri)."""


def pdf(sayfalar, font="Helvetica"):
    """sayfalar: [[(punto, metin, y), ...], ...]; boş liste = boş sayfa; ("CIZIM",) = yalnız vektör dikdörtgen."""
    nes = ["<< /Type /Catalog /Pages 2 0 R >>", None]
    kids = []
    for sayfa in sayfalar:
        if sayfa == ("CIZIM",):
            akis = "4 w 50 50 495 742 re S"
        else:
            akis = "BT\n" + "".join(f"/F1 {p} Tf 1 0 0 1 72 {y} Tm ({m}) Tj\n" for p, m, y in sayfa) + "ET"
        nes.append(f"<< /Length {len(akis)} >>\nstream\n{akis}\nendstream")
        icerik = len(nes)
        nes.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {icerik} 0 R "
                   f"/Resources << /Font << /F1 FONT 0 R >> >> >>")
        kids.append(len(nes))
    nes.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{font} >>")
    font_no = len(nes)
    nes = [n.replace("FONT", str(font_no)) if n else n for n in nes]
    nes[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    out, ofs = b"%PDF-1.4\n", []
    for i, n in enumerate(nes, 1):
        ofs.append(len(out))
        out += f"{i} 0 obj\n{n}\nendobj\n".encode("latin-1")
    x = len(out)
    out += f"xref\n0 {len(nes) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in ofs).encode()
    out += f"trailer\n<< /Size {len(nes) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return out


def satirlar(punto, n=14, metin="Ogrenci notu metin satiri deneme"):
    return [(punto, metin, 760 - 40 * i) for i in range(n)]
