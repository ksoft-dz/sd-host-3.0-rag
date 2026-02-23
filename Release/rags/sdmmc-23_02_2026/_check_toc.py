import fitz

doc = fitz.open('../rm0452-spc58-h-line--32-bit-power-architecture-automotive-mcu-triple-z4-cores-200-mhz-10-mbytes-flash-hsm-asild-stmicroelectronics.pdf')
toc = doc.get_toc()
l3 = [t for t in toc if t[0] == 3]
print(f'level-3 bookmarks: {len(l3)}')
print()
for i, t in enumerate(l3):
    if i < len(l3) - 1:
        pages = l3[i + 1][2] - t[2]
    else:
        pages = '?'
    print(f"  p{t[2]:4d}  ({str(pages):>3s}p)  {t[1][:70]}")
