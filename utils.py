from config import C

def _pill(cv, x1, y1, x2, y2, r, fill):
    cv.create_arc(x1,     y1, x1+2*r, y2, start=90,  extent=180, fill=fill, outline="")
    cv.create_arc(x2-2*r, y1, x2,     y2, start=270, extent=180, fill=fill, outline="")
    cv.create_rectangle(x1+r, y1, x2-r, y2, fill=fill, outline="")

def _pcolor(p):
    if p < 30:   return C["err"]
    elif p < 70: return C["warn"]
    else:        return C["ok"]

def _lighten(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(min(r+35,255), min(g+35,255), min(b+35,255))