def compare_prices(product_variants):
    # product_variants: list of product dicts from different sources
    # return sorted by lowest price
    def price_val(p):
        try:
            return float(p.get("price", 1e9))
        except:
            return 1e9
    return sorted(product_variants, key=price_val)
