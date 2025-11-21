# standard library mapping for VM / interpreter

def gecco_print(*args):
    # print with a space between args
    print(*args)

STD_LIB = {
    "print": gecco_print,
}