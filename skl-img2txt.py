from PIL import Image
import sys

img = sys.argv[1]
outtxt = img.split(".")[-2] + "txt"
WIDTH = 32
HEIGHT = 32


char_list = list("01")
txt = ""
def get_char(r, b, g, alpha=256):
    """# 将256灰度映射到01字符上"""
    if alpha == 0:
        return ' '
    length = len(char_list)
    gray = int(0.2126 * r + 0.7152 * g + 0.0722 * b)

    unit = (256.0 + 1)/length
    return char_list[int(gray/unit)]


if __name__ == "__main__":
    im = Image.open(img)
    im = im.resize((WIDTH, HEIGHT), Image.NEAREST)
    for i in range(HEIGHT):
        for j in range(WIDTH):
            txt += get_char(*im.getpixel((j, i)))
        txt += '\n'

    print txt

    with open(outtxt,'w') as wf:
        wf.write(txt)
