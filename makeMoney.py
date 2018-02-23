#coding: utf-8

from math import pow

#  stock account
base = 4000
# how many money put in every month
putIn = 1000
# expect return every month
e = 0.1
# total money
total = 40000


def calc(p=12, e=0.1):
    """Calculate expect money
    Calculate the accumulative money with specify expect return in specify period

    Args:
        p: an period, unit is month
        e: expect return

    Returns:
        None
    """
    global base, total

    for i in range(1, p + 1):
        r = base * e
        print("Period: {}".format(i))
        print("  Return: {}".format(r))
        base = base + r + putIn
        print("  Base: {}".format(base))
        total = total + 10000 + base
        print("  Total: {}".format(total))

    comp = pow(1 + e, p)
    print("Compound interest:{}\nPeriod:{}\nExpect return:{}".format(comp, p, e))


if __name__ == "__main__":
    calc()

