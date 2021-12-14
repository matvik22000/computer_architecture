def get_register(x):
    x = int(x)
    if x == 0: return "zero"
    elif x == 1: return "ra"
    elif x == 2: return "sp"
    elif x == 3: return "gp"
    elif x == 4: return "tp"
    elif 5 <= x <= 7: return f"t{x-5}"
    elif 8 <= x <= 9: return f"s{x-8}"
    elif 10 <= x <= 17: return f"a{x-10}"
    elif 18 <= x <= 27: return f"s{x-16}"
    elif 28 <= x <= 31: return f"t{x-25}"
