from pdfmajor.utils import mult_matrix, translate_matrix, Bbox, apply_matrix_pt, isnumber
from ....state import PDFTextState, PDFColor

def decode_text_seq(seq: bytearray, ctm: tuple, textstate: PDFTextState, color: PDFColor):
    textstate.matrix = mult_matrix(textstate.matrix, ctm)
    textstate.scaling = textstate.scaling * .01
    textstate.charspace = textstate.charspace * textstate.scaling
    textstate.wordspace = textstate.wordspace * textstate.scaling
    
    if textstate.font.is_multibyte():
        textstate.wordspace = 0
    dxscale = .001 * textstate.fontsize * textstate.scaling

    if textstate.font.is_vertical():
        return __render_string_along(1,
            seq, textstate, dxscale, color
        )
    else:
        return __render_string_along(0,
            seq, textstate, dxscale, color
        )

def __render_string_along(idx: int, seq: bytearray, 
    textstate: PDFTextState, dxscale: float, color: PDFColor):
    needcharspace = False
    char_meta_datas = []
    for obj in seq:
        if isnumber(obj):
            textstate.linematrix[idx] -= obj*dxscale
            needcharspace = True
        else:
            for cid in textstate.font.decode(obj):
                if needcharspace:
                    textstate.linematrix[idx] += textstate.charspace
                
                text = textstate.font.to_unichr(cid)
                assert isinstance(text, str), str(type(text))

                matrix = translate_matrix(textstate.matrix, textstate.linematrix)
                adv, bbox = __compute_char_bbox(matrix, cid, textstate)
                textstate.linematrix[idx] += adv

                char_meta_datas.append(
                    ( text, Bbox.from_points(bbox), )
                )
                if cid == 32 and textstate.wordspace:
                    textstate.linematrix[idx] += textstate.wordspace
                needcharspace = True
                
    return (char_meta_datas, textstate, color)

def __compute_char_bbox(matrix, char_id: int, textstate: PDFTextState):
    font = textstate.font
    fontsize = textstate.fontsize
    rise = textstate.rise
    scaling = textstate.scaling

    textwidth = font.char_width(char_id)
    textdisp = font.char_disp(char_id)
    adv = textwidth * fontsize * scaling

    # compute the boundary rectangle.
    if font.is_vertical():
        # vertical
        width = font.get_width() * fontsize
        (vx, vy) = textdisp
        if vx is None:
            vx = width * 0.5
        else:
            vx = vx * fontsize * .001
        vy = (1000 - vy) * fontsize * .001
        tx = -vx
        ty = vy + rise
        bll = (tx, ty+adv)
        bur = (tx+width, ty)
    else:
        # horizontal
        height = font.get_height() * fontsize
        descent = font.get_descent() * fontsize
        ty = descent + rise
        bll = (0, ty)
        bur = (adv, ty+height)
    (x0, y0) = apply_matrix_pt(matrix, bll)
    (x1, y1) = apply_matrix_pt(matrix, bur)
    if x1 < x0:
        (x0, x1) = (x1, x0)
    if y1 < y0:
        (y0, y1) = (y1, y0)
    
    return (adv, ((x0, y0), (x1, y1)))