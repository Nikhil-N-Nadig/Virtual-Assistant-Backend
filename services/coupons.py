def best_coupon(cart, coupons):
    # cart: list of items with price; coupons: list of dicts {code, type, value, min_purchase}
    total = sum([float(i['price']) for i in cart])
    best_saving = 0
    best_coupon = None
    for c in coupons:
        if total < c.get("min_purchase",0): continue
        if c['type'] == 'percent':
            saving = total * (c['value']/100)
        else:
            saving = c['value']
        if saving > best_saving:
            best_saving = saving
            best_coupon = c
    return best_coupon, best_saving
